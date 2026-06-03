import random
from datetime import timedelta
from django.utils import timezone

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string 
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse
from django.utils.text import slugify
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt

# Rest Framework
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import UserSerializer

# Transbank
from transbank.webpay.oneclick.mall_inscription import MallInscription
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.options import WebpayOptions
from transbank.common.integration_type import IntegrationType
# Transbank Webpay Plus (Para pagos únicos / abonos)
from transbank.webpay.webpay_plus.transaction import Transaction

# Modelos
from .models import Client, User
from businesses.models import Business, UserBusiness, BusinessHour, Service, Appointment

#Reservas
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from datetime import datetime, date

from django.utils.dateparse import parse_datetime
from django.utils.timezone import make_aware





User = get_user_model()

# ==========================================
# VISTAS PÚBLICAS
# ==========================================
def home_view(request):
    """ Renderiza la landing page principal con el modal de login y registro. """
    return render(request, 'users/index.html')

def pantalla_test(request):
    return render(request, 'users/test.html')

# ==========================================
# RUTAS DE VERIFICACIÓN Y AUTENTICACIÓN
# ==========================================
def verificar_correo(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "¡Cuenta verificada y activada con éxito! Bienvenido a su panel.")
        login(request, user)
        return redirect('dashboard')
    else:
        messages.error(request, "El enlace de verificación es inválido o ya ha expirado.")
        return redirect('home')

def login_user(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password:
            messages.error(request, "Por favor, ingrese su correo y contraseña.")
            return redirect('home')

        try:
            usuario_temp = User.objects.get(username=email)
            if not usuario_temp.is_active:
                messages.error(request, "Seguridad: Aún no ha verificado su cuenta. Revise su bandeja de entrada (o carpeta Spam).")
                return redirect('home')
        except User.DoesNotExist:
            pass 

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.first_name}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Credenciales incorrectas. Verifique su correo o contraseña.")
            return redirect('home')
    return redirect('home')

def logout_user(request):
    logout(request)
    messages.success(request, "Su sesión ha sido cerrada de forma segura.")
    return redirect('home')

# ==========================================
# NÚCLEO DE LA APLICACIÓN: DASHBOARD UNIFICADO
# ==========================================
@login_required(login_url='/')
def dashboard(request):
    # 1. Búsqueda de datos inicial
    relaciones = UserBusiness.objects.filter(user=request.user).select_related('business')
    user_business_rel = relaciones.first()
    has_business = user_business_rel is not None
    business_data = user_business_rel.business if has_business else None
    rol_usuario = user_business_rel.business_role if has_business else None
    seccion_activa = request.GET.get('section', 'resumen')

    # ========================================================
    # MANEJO DE FORMULARIOS (POST)
    # ========================================================
    if request.method == 'POST':
        action = request.POST.get('action')

        # [ACCIÓN STAFF]: ACTUALIZAR SU PROPIO PERFIL
        if action == 'update_staff_profile':
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            nuevo_email = request.POST.get('email')
            if nuevo_email != request.user.email:
                if User.objects.filter(email=nuevo_email).exists():
                    messages.error(request, "Este correo ya está en uso.")
                    return redirect('dashboard')
                request.user.email = nuevo_email
                request.user.username = nuevo_email
            
            nueva_clave = request.POST.get('new_password')
            if nueva_clave:
                request.user.set_password(nueva_clave)
            request.user.save()
            if nueva_clave:
                update_session_auth_hash(request, request.user)
            messages.success(request, "¡Perfil actualizado correctamente!")
            return redirect('dashboard')

        # [LÓGICA 1]: GUARDAR CONFIGURACIÓN DEL LOCAL Y PERFIL
        elif action == 'update_config' and has_business:
            # 1. Actualizar los datos personales del Dueño
            request.user.first_name = request.POST.get('first_name', request.user.first_name)
            request.user.last_name = request.POST.get('last_name', request.user.last_name)
            request.user.save()

            # 2. Actualizar los datos del Local (Business) y su SLUG dinámico
            nuevo_nombre = request.POST.get('business_name')
            if nuevo_nombre and nuevo_nombre != business_data.name:
                business_data.name = nuevo_nombre
                
                # Generamos el nuevo slug basado en el nuevo nombre
                base_slug = slugify(nuevo_nombre)
                nuevo_slug = base_slug
                contador = 1
                
                # Verificamos que el nuevo slug no exista ya en OTRO negocio
                while Business.objects.filter(slug=nuevo_slug).exclude(id=business_data.id).exists():
                    nuevo_slug = f"{base_slug}-{contador}"
                    contador += 1
                
                business_data.slug = nuevo_slug # Asignamos el nuevo slug limpio y único

            # Guardamos los demás datos
            business_data.phone = request.POST.get('phone', business_data.phone)
            business_data.email = request.POST.get('email', business_data.email)
            business_data.address = request.POST.get('address', business_data.address)
            business_data.save()

            # 3. Guardado dinámico de horarios
            for h in BusinessHour.objects.filter(business=business_data):
                open_t = request.POST.get(f'open_time_{h.day_of_week}')
                close_t = request.POST.get(f'close_time_{h.day_of_week}')
                is_open = request.POST.get(f'is_open_{h.day_of_week}') == 'on'
                
                if open_t: h.open_time = open_t
                if close_t: h.close_time = close_t
                h.is_open = is_open
                h.save()
            
            messages.success(request, "¡Configuración y perfil actualizados exitosamente!")
            return redirect('/dashboard/?section=config')

        # [LÓGICA 2]: SEGURIDAD (CLAVE / EMAIL)
        elif action == 'update_security':
            tipo_cambio = request.POST.get('tipo_cambio')
            if tipo_cambio == 'password':
                current_p = request.POST.get('current_password')
                new_p = request.POST.get('new_password')
                if request.user.check_password(current_p):
                    request.user.set_password(new_p)
                    request.user.save()
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "¡Su contraseña ha sido cambiada!")
                else:
                    messages.error(request, "Contraseña actual incorrecta.")
                return redirect('/dashboard/?section=config')
            
            elif tipo_cambio == 'email':
                nuevo_email = request.POST.get('nuevo_email')
                if User.objects.filter(email=nuevo_email).exists():
                    messages.error(request, "El correo ya está en uso.")
                    return redirect('/dashboard/?section=config')
                try:
                    usuario = request.user
                    usuario.email = nuevo_email
                    usuario.username = nuevo_email
                    usuario.is_active = False
                    usuario.save()
                    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                    token = default_token_generator.make_token(usuario)
                    enlace_seguro = request.build_absolute_uri(reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token}))
                    mensaje_html = f"<p>Active su cuenta: <a href='{enlace_seguro}'>Verificar Cuenta</a></p>"
                    send_mail('Confirme su Email', strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [nuevo_email], html_message=mensaje_html)
                    logout(request)
                    messages.success(request, "Revise su nuevo correo para activar la cuenta.")
                    return redirect('home')
                except Exception as e:
                    messages.error(request, f"Error: {e}")
                    return redirect('/dashboard/?section=config')

        # [LÓGICA 3]: AGREGAR COLABORADOR
        elif action == 'add_colaborador' and has_business:
            colaboradores_actuales = UserBusiness.objects.filter(business=business_data).exclude(business_role='owner').count()
            tiempo_operando = timezone.now() - business_data.created_at if hasattr(business_data, 'created_at') else timedelta(days=0)
            en_periodo_prueba = tiempo_operando.days <= 60

            # Lógica dinámica de planes
            limite_colaboradores = 4 if getattr(business_data, 'current_plan', 'pro') == 'pro' else 2
            
            if colaboradores_actuales >= limite_colaboradores:
                messages.error(request, f"Límite de {limite_colaboradores} colaboradores alcanzado. Actualice su plan.")
                return redirect('/dashboard/?section=colaboradores')

            email = request.POST.get('email')
            if User.objects.filter(username=email).exists():
                messages.error(request, "El correo ya está registrado.")
                return redirect('/dashboard/?section=colaboradores')
            try:
                clave_temporal = str(random.randint(100000, 999999))
                nuevo_usuario = User.objects.create_user(
                    username=email, email=email, password=clave_temporal,
                    first_name=request.POST.get('first_name'), last_name=request.POST.get('last_name')
                )
                nuevo_usuario.is_active = False
                nuevo_usuario.save()
                recibe_reservas = request.POST.get('provides_services') == 'on'
                UserBusiness.objects.create(user=nuevo_usuario, business=business_data, business_role=request.POST.get('role'))
                uid = urlsafe_base64_encode(force_bytes(nuevo_usuario.pk))
                token = default_token_generator.make_token(nuevo_usuario)
                enlace_seguro = request.build_absolute_uri(reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token}))
                mensaje_html = f"<p>Su clave temporal es: {clave_temporal}. <a href='{enlace_seguro}'>Activar Cuenta</a></p>"
                send_mail('Invitación al equipo', strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje_html)
                messages.success(request, "Invitación enviada exitosamente.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
            return redirect('/dashboard/?section=colaboradores')

        # [LÓGICA 4]: EDITAR COLABORADOR
        elif action == 'edit_colaborador' and has_business:
            try:
                ub_target = UserBusiness.objects.get(id=request.POST.get('ub_id'), business=business_data)
                ub_target.business_role = request.POST.get('role')
                ub_target.provides_services = request.POST.get('provides_services') == 'on'
                ub_target.save()
                ub_target.user.first_name = request.POST.get('first_name')
                ub_target.user.last_name = request.POST.get('last_name')
                ub_target.user.is_active = request.POST.get('is_active') == 'on'
                ub_target.user.save()
                messages.success(request, "Cambios guardados.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
            return redirect('/dashboard/?section=colaboradores')

        # [LÓGICA 5]: ELIMINAR COLABORADOR
        elif action == 'delete_colaborador' and has_business:
            try:
                ub_target = UserBusiness.objects.get(id=request.POST.get('ub_id'), business=business_data)
                ub_target.user.delete()
                messages.success(request, "Usuario eliminado permanentemente.")
            except Exception as e:
                messages.error(request, f"Error: {e}")
            return redirect('/dashboard/?section=colaboradores')

        # [LÓGICA 6]: ONBOARDING
        elif not has_business:
            name = request.POST.get('business_name')
            slug = slugify(name)
            base_slug = slug
            counter = 1
            while Business.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            try:
                nuevo_negocio = Business.objects.create(
                    name=name, slug=slug, phone=request.POST.get('phone'), 
                    email=request.POST.get('email'), address=request.POST.get('address')
                )
                UserBusiness.objects.create(user=request.user, business=nuevo_negocio, business_role='owner')
                for day in range(7):
                    es_laboral = day < 6
                    BusinessHour.objects.create(
                        business=nuevo_negocio, day_of_week=day,
                        open_time=request.POST.get('opening_time') if es_laboral else "09:00",
                        close_time=request.POST.get('closing_time') if es_laboral else "18:00",
                        is_open=es_laboral
                    )
                messages.success(request, "¡Perfil comercial inicializado!")
            except Exception as error:
                messages.error(request, f"Error: {error}")
            return redirect('dashboard')
        
        # [LÓGICA 7]: AGREGAR SERVICIO AL CATÁLOGO
        elif action == 'add_service' and has_business:
            try:
                Service.objects.create(
                    business=business_data,
                    name=request.POST.get('name'),
                    category=request.POST.get('category', ''), # Opcional
                    description=request.POST.get('description', ''), # Opcional
                    duration_minutes=int(request.POST.get('duration_minutes')),
                    price=float(request.POST.get('price'))
                )
                messages.success(request, "¡Servicio agregado al catálogo exitosamente!")
            except Exception as e:
                messages.error(request, f"Error al guardar el servicio: {e}")
            return redirect('/dashboard/?section=servicios')

        # [LÓGICA 8]: ELIMINAR SERVICIO
        elif action == 'delete_service' and has_business:
            try:
                servicio_id = request.POST.get('service_id')
                Service.objects.filter(id=servicio_id, business=business_data).delete()
                messages.success(request, "Servicio eliminado de su catálogo.")
            except Exception as e:
                messages.error(request, f"Error al eliminar: {e}")
            return redirect('/dashboard/?section=servicios')
        
        # [LÓGICA 9]: ACTUALIZAR ESTADO DE LA CITA
        elif action == 'update_status' and has_business:
            cita_id = request.POST.get('cita_id')
            nuevo_estado = request.POST.get('status')
            try:
                cita = Appointment.objects.get(id=cita_id, business=business_data)
                cita.status = nuevo_estado
                cita.save()
                messages.success(request, f"Estado de la cita actualizado a '{cita.get_status_display()}'.")
            except Exception as e:
                messages.error(request, f"Error al actualizar la cita: {e}")
            return redirect('/dashboard/?section=calendario')
        
        # [LÓGICA 10]: ACTIVAR/DESACTIVAR SERVICIOS DEL COLABORADOR
        elif action == 'toggle_services' and has_business:
            colab_id = request.POST.get('colab_id')
            try:
                colab = UserBusiness.objects.get(id=colab_id, business=business_data)
                # Invertimos el valor (Si era True pasa a False, y viceversa)
                colab.provides_services = not colab.provides_services 
                colab.save()
                
                estado = "ahora recibe citas" if colab.provides_services else "ya no recibe citas"
                messages.success(request, f"¡Actualizado! {colab.user.first_name} {estado}.")
            except Exception as e:
                messages.error(request, f"Error al actualizar colaborador: {e}")
            return redirect('/dashboard/?section=colaboradores')

    # ========================================================
    # RENDERIZADO DE LA PANTALLA (GET) Y CONTEXTO
    # ========================================================
    
    # --- PARCHE DE AUTOSANADO DE HORARIOS ---
    if has_business:
        # Si el local no tiene horarios, los creamos automáticamente ahora mismo
        if not BusinessHour.objects.filter(business=business_data).exists():
            for day in range(7):
                BusinessHour.objects.create(
                    business=business_data,
                    day_of_week=day,
                    open_time="09:00",
                    close_time="20:00",
                    is_open=(day < 6) # Abierto de Lunes a Sábado, cerrado el Domingo
                )
                
    horarios = BusinessHour.objects.filter(business=business_data).order_by('day_of_week') if has_business else []
    colaboradores = UserBusiness.objects.filter(business=business_data).select_related('user') if has_business else []
    
    # ---------------------------------------------
    # VARIABLES SAAS (PLAN PRO, STAFF LIMITS Y BI)
    # ---------------------------------------------
    dias_restantes = 0
    staff_count = 0
    max_staff = 4
    staff_percentage = 0
    cupos_libres = 4
    ultimos_digitos = "XXXX"
    comisiones_data = {
        'total_procesado_mes': "1.450.000",
        'comisiones_estilistas': "580.000",
        'tiempo_ahorrado_horas': 12,
    }

    if has_business:
        # Calculamos los colaboradores reales para la barra de progreso
        staff_count = UserBusiness.objects.filter(business=business_data).exclude(business_role='owner').count()
        staff_percentage = (staff_count / max_staff) * 100
        cupos_libres = max_staff - staff_count

        # Calculamos los días del periodo de prueba
        if getattr(business_data, 'is_in_trial', False) and getattr(business_data, 'trial_end', None):
            tiempo_restante = business_data.trial_end - timezone.now()
            dias_restantes = max(0, tiempo_restante.days)

        # Máscara de tarjeta
        card_number = getattr(business_data, 'card_number', None)
        if card_number:
            ultimos_digitos = card_number[-4:]
            
    servicios = Service.objects.filter(business=business_data).order_by('category', 'name') if has_business else []
    # Buscamos las citas reales del negocio (las más recientes primero)
    citas_recientes = Appointment.objects.filter(business=business_data).select_related('service').order_by('-date')[:5] if has_business else []
    
    
    #CALENDARIO DE STAFF
    hoy = timezone.now().date()
    
    citas_calendario = Appointment.objects.filter(
        business=business_data, 
        date__date__gte=hoy
    ).select_related('client', 'service', 'staff').order_by('date') if has_business else []
    # Empaquetamos todo para enviarlo al HTML
    context = {
        'necesita_onboarding': not has_business,
        'business': business_data,
        'horarios': horarios,
        'colaboradores': colaboradores,
        'seccion_activa': seccion_activa,
        'rol_usuario': rol_usuario,
        'mis_lugares_trabajo': relaciones,
        # Variables SaaS para la pestaña Resumen
        'dias_restantes': dias_restantes,
        'staff_count': staff_count,
        'max_staff': max_staff,
        'staff_percentage': staff_percentage,
        'cupos_libres': cupos_libres,
        'comisiones': comisiones_data,
        'ultimos_digitos': ultimos_digitos,
        #Servicios
        'servicios': servicios,
        #Reservas
        'citas_recientes': citas_recientes,
        'citas_calendario': citas_calendario,
    }
    
    # Enrutamiento dinámico según el Rol
    if rol_usuario == 'staff':
        citas_staff = Appointment.objects.filter(staff=request.user).order_by('-date')
        context['total_ganado'] = citas_staff.aggregate(Sum('price'))['price__sum'] or 0
        return render(request, 'businesses/dashboard_staff.html', context)
    else:
        return render(request, 'businesses/dashboard_owner.html', context)

# ========================================================
# API DE REGISTRO UNIFICADO CON TRANSBANK WEBPAY
# ========================================================
class RegistroUsuarioAPI(APIView):
    def post(self, request):
        email = request.data.get('email')
        if email:
            User.objects.filter(email=email, is_active=False).delete()
            
        serializer = UserSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        usuario = serializer.save()
        usuario.is_active = False
        usuario.save()
        rol = request.data.get('role', 'client')

        if rol == 'owner':
            try:
                tx = MallInscription(WebpayOptions(
                    commerce_code=IntegrationCommerceCodes.ONECLICK_MALL,
                    api_key=IntegrationApiKeys.WEBPAY,
                    integration_type=IntegrationType.TEST
                ))
                url_retorno = request.build_absolute_uri(f'/api/registro/transbank-confirm/?u={usuario.username}')
                respuesta_tbk = tx.start(username=usuario.username, email=usuario.email, response_url=url_retorno)
                
                return Response({
                    "mensaje": "Redirigiendo a Webpay...",
                    "requiere_redireccion": True,
                    "url_webpay": respuesta_tbk.get('url_webpay'),
                    "token": respuesta_tbk.get('token')
                }, status=status.HTTP_201_CREATED)
            except Exception as e:
                usuario.delete() 
                return Response({"error": f"Error Transbank: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if rol == 'client':
            try:
                uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                token = default_token_generator.make_token(usuario)
                enlace_seguro = request.build_absolute_uri(reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token}))
                
                mensaje_html = f"<div style='padding: 20px;'><h2 style='color: #0A2647;'>¡Bienvenido!</h2><p><a href='{enlace_seguro}' style='background-color: #F58220; color: white; padding: 12px 25px; text-decoration: none;'>VERIFICAR MI CUENTA</a></p></div>"
                send_mail('Verifique su cuenta', strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [usuario.email], html_message=mensaje_html)
                
                return Response({"mensaje": "¡Registro exitoso! Revise su correo."}, status=status.HTTP_201_CREATED)
            except Exception as e:
                usuario.delete()
                return Response({"error": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
@csrf_exempt
def transbank_confirm(request):
    token = request.POST.get('TBK_TOKEN') or request.GET.get('TBK_TOKEN')
    username_from_url = request.GET.get('u')
    
    if not token:
        messages.error(request, "No se recibió un token válido.")
        return redirect('/')

    try:
        tx = MallInscription(WebpayOptions(
            commerce_code=IntegrationCommerceCodes.ONECLICK_MALL,
            api_key=IntegrationApiKeys.WEBPAY,
            integration_type=IntegrationType.TEST
        ))
        resultado = tx.finish(token)
        response_code = resultado.get('response_code') if isinstance(resultado, dict) else resultado.response_code
        
        if response_code == 0:
            usuario = User.objects.get(username=username_from_url)
            tbk_user = resultado.get('tbk_user') if isinstance(resultado, dict) else getattr(resultado, 'tbk_user', '')
            card_number = resultado.get('card_number') if isinstance(resultado, dict) else getattr(resultado, 'card_number', 'XXXX')
            
            fecha_termino_trial = timezone.now() + timedelta(days=60)
            nombre_salon = f"Salón de {usuario.first_name}"
            slug_seguro = slugify(f"{nombre_salon}-{usuario.id}")
            
            # CORRECCIÓN: Creamos el negocio primero, sin usar el campo 'owner' inexistente
            business = Business.objects.create(
                name=nombre_salon,
                slug=slug_seguro,
                plan_type='pro',
                is_in_trial=True,
                trial_end=fecha_termino_trial,
                tbk_user=tbk_user,
                card_number=card_number
            )
            
            # CORRECCIÓN: Vinculamos al dueño mediante la tabla puente UserBusiness
            UserBusiness.objects.create(
                user=usuario,
                business=business,
                business_role='owner'
            )
            
            # Envío de correo y redirección...
            uid = urlsafe_base64_encode(force_bytes(usuario.pk))
            token_email = default_token_generator.make_token(usuario)
            enlace_seguro = request.build_absolute_uri(reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token_email}))
            mensaje_html = f"""
                            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                                <h2 style="color: #0A2647; text-align: center;">¡Tarjeta vinculada con éxito!</h2>
                                <p>Hola <strong>{usuario.first_name}</strong>,</p>
                                <p>Su tarjeta de crédito ha sido inscrita correctamente mediante Webpay Oneclick.</p>
                                <p><strong>Su periodo de evaluación gratuita de 2 meses ha comenzado oficialmente hoy.</strong></p>
                                <p>Para activar su acceso definitivo al panel administrativo, confirme su correo presionando el siguiente enlace:</p>
                                <div style="text-align: center; margin: 30px 0;">
                                    <a href="{enlace_seguro}" style="background-color: #F58220; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block;">ACTIVAR MI CUENTA</a>
                                </div>
                            </div>
                        """
            send_mail('Active su cuenta - SmartBooking HUB', strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [usuario.email], html_message=mensaje_html)
            
            messages.success(request, "¡Tarjeta verificada con éxito! Revise su correo para activar su perfil comercial.")
            return redirect('/')
            
        else:
            messages.error(request, "La inscripción fue rechazada en Webpay.")
            return redirect('/')
            
    except Exception as e:
        print(f"🔥 ERROR EN TRANSBANK CONFIRM: {str(e)}")
        messages.error(request, "Error crítico durante la confirmación bancaria.")
        return redirect('/')
    
# ========================================================
# PORTAL PÚBLICO DEL CLIENTE (RESERVAS)
# ========================================================
def public_booking(request, business_slug):
    # 1. Buscamos el negocio por su URL amigable (slug)
    business = get_object_or_404(Business, slug=business_slug)
    
    # 2. Obtenemos solo los servicios activos
    servicios = Service.objects.filter(business=business, is_active=True).order_by('category', 'name')
    
    # 3. Obtenemos al personal que trabaja allí (Staff, Managers y Dueños)
    staff_disponible = UserBusiness.objects.filter(business=business, user__is_active=True, provides_services=True)
    
    # 4. Obtenemos los horarios en que el local está abierto
    horarios_activos = BusinessHour.objects.filter(business=business, is_open=True).order_by('day_of_week')

    context = {
        'business': business,
        'servicios': servicios,
        'staff_list': staff_disponible,
        'horarios': horarios_activos,
    }
    
    # Renderizamos una nueva plantilla diseñada exclusivamente para el cliente final
    return render(request, 'businesses/public_booking.html', context)

# ========================================================
# API DE DISPONIBILIDAD MATEMÁTICA
# ========================================================
def get_available_slots(request, business_slug):
    """
    Calcula los bloques disponibles basándose en el horario del local, 
    la duración del servicio, y filtra estrictamente horas en el pasado.
    """
    fecha_str = request.GET.get('date')
    servicio_id = request.GET.get('service_id')
    
    if not fecha_str or not servicio_id:
        return JsonResponse({'error': 'Faltan parámetros'}, status=400)

    try:
        fecha_obj = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        dia_semana = fecha_obj.weekday()
        
        # --- BLOQUEO ESTRICTO 1: Fechas pasadas ---
        hoy = timezone.localtime(timezone.now()).date()
        if fecha_obj < hoy:
            return JsonResponse({'slots': [], 'mensaje': 'No se pueden agendar fechas en el pasado.'})

        business = Business.objects.get(slug=business_slug)
        servicio = Service.objects.get(id=servicio_id, business=business)
        horario_dia = BusinessHour.objects.get(business=business, day_of_week=dia_semana)

        if not horario_dia.is_open or not horario_dia.open_time or not horario_dia.close_time:
            return JsonResponse({'slots': [], 'mensaje': 'El local se encuentra cerrado en este día.'})

        # --- MOTOR MATEMÁTICO DE BLOQUES ---
        dummy_date = datetime.today()
        current_dt = datetime.combine(dummy_date, horario_dia.open_time)
        end_dt = datetime.combine(dummy_date, horario_dia.close_time)

        slots_disponibles = []
        intervalo = timedelta(minutes=30)
        duracion_servicio = timedelta(minutes=servicio.duration_minutes)

        # Variables para filtrar las horas de HOY
        es_hoy = (fecha_obj == hoy)
        hora_actual = timezone.localtime(timezone.now()).time()
        citas_del_dia = Appointment.objects.filter(business=business, date=fecha_obj)
        
        horas_ocupadas = set()

        # Mapeamos todos los bloques de tiempo que ya están ocupados
        for cita in citas_del_dia:
            # Recreamos la hora de inicio y fin de la cita existente
            cita_start = datetime.combine(fecha_obj, cita.time)
            cita_end = cita_start + timedelta(minutes=cita.service.duration_minutes)
            
            temp_time = cita_start
            while temp_time < cita_end:
                horas_ocupadas.add(temp_time.time())
                temp_time += timedelta(minutes=30) # Asumimos bloques de 30 min

        # --- MOTOR MATEMÁTICO DE BLOQUES ---
        dummy_date = datetime.today()
        current_dt = datetime.combine(dummy_date, horario_dia.open_time)
        end_dt = datetime.combine(dummy_date, horario_dia.close_time)

        slots_disponibles = []
        intervalo = timedelta(minutes=30)
        duracion_servicio = timedelta(minutes=servicio.duration_minutes)

        es_hoy = (fecha_obj == hoy)
        hora_actual = timezone.localtime(timezone.now()).time()

        while current_dt + duracion_servicio <= end_dt:
            slot_time = current_dt.time()
            
            # BLOQUEO 1: Si es hoy y la hora ya pasó
            if es_hoy and slot_time <= hora_actual:
                current_dt += intervalo
                continue
                
            # BLOQUEO 2: Si este horario (o los que requiere el servicio) choca con una cita existente
            # Revisamos si algún bloque requerido por el NUEVO servicio está ocupado
            conflicto = False
            temp_check = current_dt
            while temp_check < current_dt + duracion_servicio:
                if temp_check.time() in horas_ocupadas:
                    conflicto = True
                    break
                temp_check += intervalo
                
            if conflicto:
                current_dt += intervalo
                continue # Saltamos este bloque porque choca con otra cita
            
            # Si pasó todas las pruebas de seguridad, lo mostramos
            slots_disponibles.append(slot_time.strftime('%H:%M'))
            current_dt += intervalo

        if not slots_disponibles:
            return JsonResponse({'slots': [], 'mensaje': 'Agenda completa o sin bloques suficientes.'})

        return JsonResponse({'slots': slots_disponibles})


    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
# ========================================================
# PROCESAMIENTO FINAL DE LA RESERVA
# ========================================================
def confirm_booking(request, business_slug):
    if request.method == 'POST':
        business = get_object_or_404(Business, slug=business_slug)
        
        # 1. Obtenemos los datos del formulario
        service_id = request.POST.get('service_id')
        staff_id = request.POST.get('staff_id')
        fecha = request.POST.get('date')
        hora = request.POST.get('time')
        
        f_name = request.POST.get('first_name')
        l_name = request.POST.get('last_name')
        tipo_pago = request.POST.get('tipo_pago')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        fecha_hora_str = f"{fecha}T{hora}" 
        fecha_hora_obj = make_aware(parse_datetime(fecha_hora_str))

        try:
            servicio = Service.objects.get(id=service_id, business=business)
                
            # 2. Creamos o buscamos al Cliente (¡AÑADIMOS EL BUSINESS!)
            cliente, created = Client.objects.get_or_create(
                email=email,
                business=business, # <--- Esta es la línea mágica que faltaba
                defaults={'first_name': f_name, 'last_name': l_name, 'phone': phone}
            )

            # 3. Asignar Staff (Lógica "Cualquiera Disponible")
            staff_asignado = None
            if staff_id and staff_id != 'any':
                staff_asignado = User.objects.get(id=staff_id)
            else:
                # Buscamos a todo el staff del negocio que esté activo
                # (A futuro aquí filtraremos a los que tienen el toggle de "atiende" habilitado)
                staff_disponible = UserBusiness.objects.filter(business=business, user__is_active=True, provides_services=True)
                    
                if staff_disponible.exists():
                    # Aquí deberíamos cruzar con el calendario para ver quién está libre a esa hora exacta.
                    # Por ahora, para que el flujo avance, elegimos uno al azar de los disponibles.
                    colaborador_random = random.choice(staff_disponible)
                    staff_asignado = colaborador_random.user

            # 4. GUARDAR LA CITA
            estado_inicial = 'pending_payment' if tipo_pago == 'abono' else 'pending'
            cita = Appointment.objects.create(
                business=business,
                service=servicio,
                client=cliente,
                staff=staff_asignado,
                date=fecha_hora_obj,
                price=servicio.price,
                status=estado_inicial
            )

            # 5. BIFURCACIÓN: REDIRECCIÓN A PAGO O CORREO DE CONFIRMACIÓN
            if tipo_pago == 'abono':
                # [FLUJO TRANSBANK]: Calculamos el 50% del total
                monto_abono = int(servicio.price) // 2 # Transbank exige enteros sin decimales
                
                # Datos obligatorios para Webpay
                orden_compra = f"CITA-{cita.id}"
                session_id = f"CLIENTE-{cliente.id}"
                url_retorno = request.build_absolute_uri(reverse('webpay_return', kwargs={'business_slug': business.slug}))
                
                # Generamos la URL a la que Webpay devolverá al cliente tras pagar
                url_retorno = request.build_absolute_uri(reverse('webpay_return', kwargs={'business_slug': business.slug}))
                
                try:
                    opciones_tx = WebpayOptions(
                        IntegrationCommerceCodes.WEBPAY_PLUS, 
                        IntegrationApiKeys.WEBPAY, 
                        IntegrationType.TEST
                    )
                    tx = Transaction(opciones_tx)
                    
                    response = tx.create(
                        buy_order=orden_compra, 
                        session_id=session_id, 
                        amount=monto_abono, 
                        return_url=url_retorno
                    )
                    
                    # CORRECCIÓN: Extraemos los datos como diccionario
                    url_tbk = response.get('url')
                    token_ws = response.get('token')
                    
                    return redirect(f"{url_tbk}?token_ws={token_ws}")
                    
                except Exception as e:
                    cita.delete()
                    print(f"🚨 ERROR TRANSBANK CREAR: {e}")
                    messages.error(request, f"Error al conectar con Webpay: {e}")
                    return redirect('public_booking', business_slug=business.slug)
                
            else:
                # [FLUJO PAGO EN LOCAL]: Confirmamos de inmediato y enviamos el correo que armaste
                nombre_staff = f"{staff_asignado.first_name} {staff_asignado.last_name}" if staff_asignado else "Nuestro equipo"
                
                # Construye la URL completa hacia tu logo estático
                logo_url = request.build_absolute_uri('/static/img/logo.png')
                
                # Preparamos el contenido del correo
                asunto = f"Confirmación de Reserva en {business.name}"
                # Diseño Elegante del Correo
                mensaje_html = f"""
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eaeaea; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                    
                    <div style="background-color: #0A2647; padding: 25px; text-align: center;">
                        <img src="{logo_url}" alt="SmartBooking HUB" style="max-width: 220px; height: auto;">
                    </div>
                    
                    <div style="padding: 30px; background-color: #ffffff; color: #333333;">
                        <h2 style="color: #F58220; margin-top: 0; font-size: 22px;">¡Hola {cliente.first_name}!</h2>
                        <p style="font-size: 16px; line-height: 1.5;">Tu reserva en <strong>{business.name}</strong> ha sido confirmada con éxito.</p>
                        
                        <div style="background-color: #f8f9fa; border-left: 4px solid #F58220; padding: 20px; margin: 25px 0; border-radius: 0 8px 8px 0;">
                            <h3 style="margin-top: 0; color: #0A2647; font-size: 18px;">Detalles de tu cita:</h3>
                            <ul style="list-style-type: none; padding: 0; margin: 0; font-size: 15px; line-height: 1.8;">
                                <li><strong style="color:#0A2647;">✂️ Servicio:</strong> {servicio.name}</li>
                                <li><strong style="color:#0A2647;">📅 Fecha:</strong> {fecha}</li>
                                <li><strong style="color:#0A2647;">⏰ Hora:</strong> {hora} hrs</li>
                                <li><strong style="color:#0A2647;">👤 Especialista:</strong> {nombre_staff}</li>
                                <li><strong style="color:#0A2647;">📍 Dirección:</strong> {business.address}</li>
                            </ul>
                        </div>
                        
                        <p style="font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 15px;"><strong>Pago pendiente:</strong> 100% en el local (${int(servicio.price):,.0f}).</p>
                        <p style="color: #888888; font-size: 14px; margin-top: 20px;">Si necesitas cancelar o modificar tu hora, por favor contáctanos con anticipación. ¡Te esperamos!</p>
                    </div>
                    
                    <div style="background-color: #f1f1f1; padding: 20px; text-align: center; color: #999999; font-size: 12px;">
                        <p style="margin: 0;">Este es un mensaje automático. Por favor no respondas a este correo.</p>
                        <p style="margin: 5px 0 0 0;">Desarrollado por <strong>SmartBooking HUB</strong></p>
                    </div>
                </div>
                """.replace(',', '.') # Reemplaza la coma de los miles por un punto para el formato chileno
                
                mensaje_texto = strip_tags(mensaje_html)

                try:
                    send_mail(
                        subject=asunto,
                        message=mensaje_texto,
                        html_message=mensaje_html,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[cliente.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    # Si falla el correo (por ej. falta configurar SMTP), la cita se guarda igual
                    print(f"Error al enviar correo: {e}")
                    
                messages.success(request, f"¡Reserva confirmada con éxito para el {fecha} a las {hora}! Le hemos enviado un correo con los detalles.")
                return redirect('public_booking', business_slug=business.slug)

        except Exception as e:
            # ESTE ES EL EXCEPT PRINCIPAL QUE FALTABA
            messages.error(request, f"Ocurrió un error al procesar su reserva: {e}")
            return redirect('public_booking', business_slug=business.slug)
            
    return redirect('public_booking', business_slug=business_slug)

# ========================================================
# RESPUESTA DE WEBPAY PARA ABONOS DE CLIENTES
# ========================================================
def webpay_return(request, business_slug):
    token = request.GET.get('token_ws')
    
    if not token:
        messages.error(request, "Pago cancelado. Tu reserva no fue confirmada.")
        return redirect('public_booking', business_slug=business_slug)

    try:
        opciones_tx = WebpayOptions(
            IntegrationCommerceCodes.WEBPAY_PLUS, 
            IntegrationApiKeys.WEBPAY, 
            IntegrationType.TEST
        )
        tx = Transaction(opciones_tx)
        
        # Confirmamos el pago (devuelve un diccionario)
        response = tx.commit(token)
        
        # CORRECCIÓN: Extraemos los datos del diccionario de forma segura
        status = response.get('status')
        response_code = response.get('response_code')
        buy_order = response.get('buy_order', '')
        amount = response.get('amount', 0)
        
        # Recuperamos la cita
        cita_id = buy_order.replace('CITA-', '')
        cita = Appointment.objects.get(id=cita_id)
        business = cita.business
        cliente = cita.client

        if status == 'AUTHORIZED' and response_code == 0:
            # ¡PAGO EXITOSO! 
            cita.status = 'pending'
            cita.save()

            nombre_staff = f"{cita.staff.first_name} {cita.staff.last_name}" if cita.staff else "Nuestro equipo"
            fecha_str = cita.date.strftime('%d-%m-%Y')
            hora_str = cita.date.strftime('%H:%M')
            saldo_restante = cita.price - amount
            
            # Construye la URL completa hacia tu logo estático
            logo_url = request.build_absolute_uri('/static/img/logo.png')
            
            asunto = f"¡Reserva y Abono Confirmados en {business.name}!"
            # Diseño Elegante del Correo
            mensaje_html = f"""
            <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #eaeaea; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">
                <div style="background-color: #0A2647; padding: 25px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; letter-spacing: 1px;">SmartBooking HUB</h1>
                </div>
                
                <div style="padding: 30px; background-color: #ffffff; color: #333333;">
                    <h2 style="color: #F58220; margin-top: 0; font-size: 22px;">¡Hola {cliente.first_name}!</h2>
                    <p style="font-size: 16px; line-height: 1.5;">Hemos recibido tu abono seguro vía Webpay por <strong>${int(amount):,.0f}</strong>.</p>
                    
                    <div style="background-color: #f8f9fa; border-left: 4px solid #F58220; padding: 20px; margin: 25px 0; border-radius: 0 8px 8px 0;">
                        <h3 style="margin-top: 0; color: #0A2647; font-size: 18px;">Tu cita está asegurada:</h3>
                        <ul style="list-style-type: none; padding: 0; margin: 0; font-size: 15px; line-height: 1.8;">
                            <li><strong style="color:#0A2647;">✂️ Servicio:</strong> {cita.service.name}</li>
                            <li><strong style="color:#0A2647;">📅 Fecha:</strong> {fecha_str}</li>
                            <li><strong style="color:#0A2647;">⏰ Hora:</strong> {hora_str} hrs</li>
                            <li><strong style="color:#0A2647;">👤 Especialista:</strong> {nombre_staff}</li>
                            <li><strong style="color:#0A2647;">📍 Dirección:</strong> {business.address}</li>
                        </ul>
                    </div>
                    
                    <p style="font-size: 16px; border-bottom: 1px solid #eee; padding-bottom: 15px;">Queda un saldo pendiente de <strong>${int(saldo_restante):,.0f}</strong> que se pagará el día de tu visita.</p>
                    <p style="color: #888888; font-size: 14px; margin-top: 20px;">¡Gracias por tu preferencia, te esperamos!</p>
                </div>
                
                <div style="background-color: #f1f1f1; padding: 20px; text-align: center; color: #999999; font-size: 12px;">
                    <p style="margin: 0;">Comprobante de pago válido emitido electrónicamente.</p>
                    <p style="margin: 5px 0 0 0;">Desarrollado por <strong>SmartBooking HUB</strong></p>
                </div>
            </div>
            """.replace(',', '.') # Formato chileno
            
            mensaje_texto = strip_tags(mensaje_html)

            try:
                send_mail(subject=asunto, message=mensaje_texto, html_message=mensaje_html, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[cliente.email])
            except Exception as e:
                print(f"Error correo Transbank: {e}")

            messages.success(request, "¡Abono procesado exitosamente! Tu hora está asegurada y te hemos enviado el comprobante a tu correo.")
            
        else:
            # PAGO RECHAZADO
            cita.delete() 
            messages.error(request, "El pago fue rechazado por su banco. La reserva no ha sido confirmada.")

    except Exception as e:
        messages.error(request, f"Ocurrió un error al procesar el pago: {e}")

    return redirect('public_booking', business_slug=business_slug)
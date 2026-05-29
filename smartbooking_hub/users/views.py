from django.contrib.auth import models
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string 
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.text import slugify
from businesses.models import Business, UserBusiness, BusinessHour
from django.contrib.auth.models import User
import random
from django.contrib.auth import update_session_auth_hash
from django.db.models import Sum
from businesses.models import Business, UserBusiness, BusinessHour, Service, Appointment

# Llama dinámicamente al modelo de usuario activo de tu proyecto
User = get_user_model()

def home_view(request):
    """
    Renderiza la landing page principal con el modal de login y registro.
    """
    return render(request, 'users/index.html')


# ==========================================
# RUTAS DE VERIFICACIÓN Y DASHBOARD
# ==========================================

def dashboard(request):
    # 1. Buscamos todas las relaciones del usuario para saber en cuántos locales trabaja
    relaciones = UserBusiness.objects.filter(user=request.user).select_related('business')
    user_business_rel = relaciones.first()
    has_business = user_business_rel is not None
    business_data = user_business_rel.business if has_business else None
    rol_usuario = user_business_rel.business_role if has_business else None
    # ... dentro de tu función dashboard, después de definir has_business ...
    if rol_usuario == 'staff':
        # Buscamos citas donde este usuario es el staff
        citas_staff = Appointment.objects.filter(staff=request.user).order_by('-date')
        
        # Calculamos la suma total
        total_ganado = citas_staff.aggregate(Sum('price'))['price__sum'] or 0
        
        return render(request, 'businesses/dashboard_staff.html')

    if request.method == 'POST':
        action = request.POST.get('action')

        # ========================================================
        # ACCIÓN EXCLUSIVA STAFF: ACTUALIZAR SU PROPIO PERFIL
        # ========================================================
        if action == 'update_staff_profile':
            request.user.first_name = request.POST.get('first_name')
            request.user.last_name = request.POST.get('last_name')
            
            nuevo_email = request.POST.get('email')
            # Si cambia el correo, validamos que no exista
            if nuevo_email != request.user.email:
                if User.objects.filter(email=nuevo_email).exists():
                    messages.error(request, "Este correo electrónico ya está en uso.")
                    return redirect('dashboard')
                request.user.email = nuevo_email
                request.user.username = nuevo_email
            
            # Cambio opcional de contraseña
            nueva_clave = request.POST.get('new_password')
            if nueva_clave:
                request.user.set_password(nueva_clave)
                
            request.user.save()
            
            if nueva_clave:
                update_session_auth_hash(request, request.user)
                
            messages.success(request, "¡Su perfil ha sido actualizado correctamente!")
            return redirect('dashboard')

        # ========================================================
        # LÓGICA 1: GUARDAR CAMBIOS DE CONFIGURACIÓN DEL LOCAL
        # ========================================================
        elif action == 'update_config' and has_business:
            business_data.phone = request.POST.get('phone')
            business_data.email = request.POST.get('email')
            business_data.address = request.POST.get('address')
            business_data.save()

            for day in range(7):
                horario = BusinessHour.objects.get(business=business_data, day_of_week=day)
                open_t = request.POST.get(f'open_time_{day}')
                close_t = request.POST.get(f'close_time_{day}')
                is_open = request.POST.get(f'is_open_{day}') == 'on' 

                if open_t: horario.open_time = open_t
                if close_t: horario.close_time = close_t
                horario.is_open = is_open
                horario.save()

            messages.success(request, "¡Configuración y horarios actualizados correctamente!")
            return redirect('/dashboard/?section=config')

        # ========================================================
        # LÓGICA 2: AUTOSERVICIO DE SEGURIDAD (CAMBIAR CLAVE / EMAIL)
        # ========================================================
        elif action == 'update_security':
            tipo_cambio = request.POST.get('tipo_cambio')
            
            # A) CAMBIO DE CONTRASEÑA
            if tipo_cambio == 'password':
                current_p = request.POST.get('current_password')
                new_p = request.POST.get('new_password')
                
                if request.user.check_password(current_p):
                    request.user.set_password(new_p)
                    request.user.save()
                    # Evita que se cierre la sesión del usuario al cambiar la clave
                    update_session_auth_hash(request, request.user)
                    messages.success(request, "¡Su contraseña ha sido cambiada con éxito!")
                else:
                    messages.error(request, "La contraseña actual ingresada es incorrecta.")
                return redirect('/dashboard/?section=config')
            
            # B) CAMBIO DE CORREO ELECTRÓNICO (REQUIERE VERIFICACIÓN NUEVA)
            elif tipo_cambio == 'email':
                nuevo_email = request.POST.get('nuevo_email')
                if User.objects.filter(email=nuevo_email).exists():
                    messages.error(request, "Este correo electrónico ya está en uso por otro usuario.")
                    return redirect('/dashboard/?section=config')
                
                try:
                    # Guardamos el nuevo correo, cambiamos su username y apagamos la cuenta hasta verificar
                    usuario = request.user
                    usuario.email = nuevo_email
                    usuario.username = nuevo_email
                    usuario.is_active = False
                    usuario.save()

                    # Fabricamos el token dinámico de activación
                    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
                    token = default_token_generator.make_token(usuario)
                    enlace_seguro = request.build_absolute_uri(
                        reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token})
                    )

                    # Despachamos el correo informativo
                    asunto = 'Confirme su nuevo Correo Corporativo - SmartBooking HUB'
                    mensaje_html = f"<p>Hola {usuario.first_name}, ha solicitado cambiar su correo. Para activar su cuenta con esta nueva dirección, haga clic aquí: <a href='{enlace_seguro}'>Verificar Cuenta</a></p>"
                    
                    send_mail(asunto, strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [nuevo_email], html_message=mensaje_html)
                    
                    # Al quedar desactivado, lo deslogueamos forzosamente para que vaya a su correo
                    logout(request)
                    messages.success(request, f"Se ha enviado un enlace de activación a su nuevo correo: {nuevo_email}. Verifíquelo para volver a ingresar.")
                    return redirect('home')
                except Exception as e:
                    messages.error(request, f"Error al procesar el cambio de correo: {e}")
                    return redirect('/dashboard/?section=config')

        # ========================================================
        # LÓGICA 3: AGREGAR NUEVO COLABORADOR (CON CREDENCIALES AUTO)
        # ========================================================
        elif action == 'add_colaborador' and has_business:
            email = request.POST.get('email')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            role = request.POST.get('role')

            if User.objects.filter(username=email).exists():
                messages.error(request, "Esta dirección de correo ya tiene un usuario registrado en el sistema.")
                return redirect('/dashboard/?section=colaboradores')

            try:
                # 1. Generamos una contraseña numérica temporal de 6 dígitos al azar
                clave_temporal = str(random.randint(100000, 999999))
                
                # 2. Creamos al usuario apagado (is_active=False) hasta que valide el link
                nuevo_usuario = User.objects.create_user(
                    username=email, email=email, password=clave_temporal,
                    first_name=first_name, last_name=last_name
                )
                nuevo_usuario.is_active = False
                nuevo_usuario.save()
                
                # 3. Lo enlazamos al local comercial
                UserBusiness.objects.create(user=nuevo_usuario, business=business_data, business_role=role)
                
                # 4. Generamos token único de un solo uso
                uid = urlsafe_base64_encode(force_bytes(nuevo_usuario.pk))
                token = default_token_generator.make_token(nuevo_usuario)
                enlace_seguro = request.build_absolute_uri(
                    reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token})
                )

                # 5. Enviamos el correo con el link de verificación Y su clave temporal de 6 dígitos
                asunto = 'Invitación de Acceso a SmartBooking HUB'
                mensaje_html = f"""
                    <h3>¡Bienvenido al equipo de {business_data.name}!</h3>
                    <p>Se le ha creado un perfil operativo en el sistema.</p>
                    <p><strong>Sus credenciales temporales de acceso son:</strong></p>
                    <ul>
                        <li><strong>Usuario / Correo:</strong> {email}</li>
                        <li><strong>Contraseña Temporal:</strong> {clave_temporal}</li>
                    </ul>
                    <p>Para activar su cuenta e ingresar por primera vez, haga clic en el siguiente enlace:</p>
                    <a href="{enlace_seguro}" style="background-color:#F58220; color:white; padding:10px 20px; text-decoration:none; display:inline-block; font-weight:bold;">ACTIVAR MI CUENTA</a>
                    <p>Una vez dentro, recuerde cambiar su contraseña en la pestaña de Configuración por motivos de seguridad.</p>
                """
                send_mail(asunto, strip_tags(mensaje_html), settings.DEFAULT_FROM_EMAIL, [email], html_message=mensaje_html)
                
                messages.success(request, f"Colaborador invitado. Se envió un correo con su acceso temporal y link de activación.")
            except Exception as e:
                messages.error(request, f"Error al procesar invitación: {e}")
                
            return redirect('/dashboard/?section=colaboradores')

        # ========================================================
        # LÓGICA 4: EDITAR COLABORADOR Y ESTADO (ACTIVO / DESACTIVADO)
        # ========================================================
        elif action == 'edit_colaborador' and has_business:
            ub_id = request.POST.get('ub_id')
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            new_role = request.POST.get('role')
            status_activo = request.POST.get('is_active') == 'on'

            try:
                actor_role = user_business_rel.business_role
                ub_target = UserBusiness.objects.get(id=ub_id, business=business_data)
                target_role_current = ub_target.business_role

                # 1. REGLAS PARA ADMINISTRADORES (Managers)
                if actor_role == 'manager' and target_role_current == 'owner':
                    messages.error(request, "Acceso denegado: Los administradores no pueden modificar al Dueño.")
                    return redirect('/dashboard/?section=colaboradores')
                if actor_role == 'manager' and new_role == 'owner':
                    messages.error(request, "Acceso denegado: Solo el Dueño puede otorgar la propiedad absoluta.")
                    return redirect('/dashboard/?section=colaboradores')
                    
                # 2. REGLAS ESTRICTAS PARA STAFF
                if actor_role == 'staff':
                    if ub_target.user != request.user:
                        messages.error(request, "Acceso denegado: Como Staff, solo puede editar sus propios datos.")
                        return redirect('/dashboard/?section=colaboradores')
                    if new_role != 'staff':
                        messages.error(request, "Acceso denegado: No tiene permisos para modificar su nivel de acceso.")
                        return redirect('/dashboard/?section=colaboradores')

                # 3. SEGURIDAD GENERAL
                if ub_target.user == request.user and not status_activo:
                    messages.error(request, "Operación denegada: No puede desactivar su propia cuenta.")
                    return redirect('/dashboard/?section=colaboradores')

                # Aplicamos cambios si pasa los filtros
                ub_target.business_role = new_role
                ub_target.save()

                ub_target.user.first_name = first_name
                ub_target.user.last_name = last_name
                ub_target.user.is_active = status_activo
                ub_target.user.save()

                messages.success(request, "¡Cambios en el colaborador guardados correctamente!")
            except Exception as e:
                messages.error(request, f"Error al actualizar: {e}")
                
            return redirect('/dashboard/?section=colaboradores')

        # ========================================================
        # LÓGICA EXTRA: ELIMINAR COLABORADOR DEFINITIVAMENTE
        # ========================================================
        elif action == 'delete_colaborador' and has_business:
            ub_id = request.POST.get('ub_id')

            try:
                actor_role = user_business_rel.business_role
                ub_target = UserBusiness.objects.get(id=ub_id, business=business_data)
                target_role_current = ub_target.business_role
                usuario_a_eliminar = ub_target.user

                # REGLAS DE NEGOCIO PARA ELIMINACIÓN
                if actor_role == 'staff':
                    messages.error(request, "Acceso denegado: El personal Staff no tiene permisos para eliminar usuarios.")
                    return redirect('/dashboard/?section=colaboradores')
                    
                if actor_role == 'manager' and target_role_current == 'owner':
                    messages.error(request, "Acceso denegado: Un administrador no puede expulsar al Dueño.")
                    return redirect('/dashboard/?section=colaboradores')

                if usuario_a_eliminar == request.user:
                    messages.error(request, "Operación denegada: No puede eliminarse a sí mismo.")
                    return redirect('/dashboard/?section=colaboradores')

                usuario_a_eliminar.delete()
                messages.success(request, f"¡El colaborador ha sido eliminado permanentemente del local!")
                
            except Exception as e:
                messages.error(request, f"Error al intentar eliminar el colaborador: {e}")
                
            return redirect('/dashboard/?section=colaboradores')

        # ========================================================
        # LÓGICA 5: ONBOARDING PRIMERA VEZ
        # ========================================================
        elif not has_business:
            name = request.POST.get('business_name')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            address = request.POST.get('address')
            open_time = request.POST.get('opening_time', '09:00')
            close_time = request.POST.get('closing_time', '19:00')

            if not name:
                messages.error(request, "El nombre del negocio es obligatorio.")
                return redirect('dashboard')

            slug = slugify(name)
            base_slug = slug
            counter = 1
            while Business.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1

            try:
                nuevo_negocio = Business.objects.create(name=name, slug=slug, phone=phone, email=email, address=address)
                UserBusiness.objects.create(user=request.user, business=nuevo_negocio, business_role='owner')

                for day in range(7):
                    es_laboral = day < 6
                    BusinessHour.objects.create(
                        business=nuevo_negocio, day_of_week=day,
                        open_time=open_time if es_laboral else "09:00",
                        close_time=close_time if es_laboral else "18:00",
                        is_open=es_laboral
                    )

                messages.success(request, "¡Perfil comercial e itinerarios inicializados con éxito!")
                return redirect('dashboard')
            except Exception as error:
                messages.error(request, f"Error en Onboarding: {error}")
                return redirect('dashboard')

    # ========================================================
    # MÉTODO GET: RENDERIZADO DEL PANEL
    # ========================================================
    horarios = BusinessHour.objects.filter(business=business_data).order_by('day_of_week') if has_business else []
    colaboradores = UserBusiness.objects.filter(business=business_data).select_related('user') if has_business else []
    seccion_activa = request.GET.get('section', 'resumen')

    context = {
        'necesita_onboarding': not has_business,
        'business': business_data,
        'horarios': horarios,
        'colaboradores': colaboradores,
        'seccion_activa': seccion_activa,
        'rol_usuario': rol_usuario,
        'mis_lugares_trabajo': relaciones, # Enviamos los locales para el panel de Staff
    }
    
    # SISTEMA DE ENRUTAMIENTO INTELIGENTE
    if rol_usuario == 'staff':
        # Redirige a la plantilla de Staff creada en el paso 2
        return render(request, 'businesses/dashboard_staff.html', context)
    else:
        # Redirige a la plantilla Administrativa
        return render(request, 'businesses/dashboard_owner.html', context)

def logout_user(request):
    """
    Cierra la sesión del usuario actual y lo devuelve a la página principal.
    """
    logout(request)
    messages.success(request, "Su sesión ha sido cerrada de forma segura.")
    return redirect('home')

def pantalla_test(request):
    """
    Renderiza la pantalla de test.html después de un registro exitoso.
    """
    return render(request, 'users/test.html')
def registro_dueno(request):
    if request.method == 'POST':
        rol = request.POST.get('userRole')
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')

        if not email or not password or not nombre:
            messages.error(request, "Todos los campos del formulario son obligatorios.")
            return redirect('home')

        try:
            if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
                messages.error(request, "Esta dirección de correo ya se encuentra registrada.")
                return redirect('home')

            nombre_partes = nombre.split(' ', 1)
            first_name = nombre_partes[0]
            last_name = nombre_partes[1] if len(nombre_partes) > 1 else ''

            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            # 1. ¡EL CANDADO! Guardamos la cuenta pero desactivada
            user.is_active = False 
            user.save()

            # 2. Generamos el token de seguridad único
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # Construimos la ruta exacta con el dominio de forma dinámica
            enlace_seguro = request.build_absolute_uri(
                reverse('verificar_correo', kwargs={'uidb64': uid, 'token': token})
            )

            asunto = 'Active su cuenta corporativa - SmartBooking HUB'
            contexto_correo = {
                'nombre': nombre,
                'url_verificacion': enlace_seguro
            }

            mensaje_html = render_to_string('users/emails/verificacion_owner.html', contexto_correo)
            mensaje_texto = strip_tags(mensaje_html)

            send_mail(
                subject=asunto,
                message=mensaje_texto,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=mensaje_html,
                fail_silently=False,
            )

            messages.success(request, f"¡Registro exitoso! Le hemos enviado un enlace de activación a {email}.")
            return redirect('pantalla_test')

        except Exception as error:
            messages.error(request, f"Ocurrió un error en el servidor: {error}")
            return redirect('home')

    return redirect('home')


def verificar_correo(request, uidb64, token):
    """
    Desencripta el enlace, valida el token de un solo uso y enciende la cuenta.
    """
    try:
        # Intentamos desencriptar el ID del usuario
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    # Si el usuario existe y su token de seguridad coincide
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "¡Cuenta verificada y activada con éxito! Bienvenido a su panel.")
        
        # Como ya verificó, lo podemos loguear automáticamente y enviarlo al dashboard
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

        # 3. VERIFICACIÓN EXTRA: Le avisamos al usuario si le falta abrir su correo
        try:
            usuario_temp = User.objects.get(username=email)
            if not usuario_temp.is_active:
                messages.error(request, "Seguridad: Aún no ha verificado su cuenta. Revise su bandeja de entrada (o carpeta Spam) y haga clic en el enlace de activación.")
                return redirect('home')
        except User.DoesNotExist:
            pass # Si no existe, dejamos que authenticate() tire el error genérico

        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, f"¡Bienvenido de nuevo, {user.first_name}!")
            return redirect('dashboard')
        else:
            messages.error(request, "Credenciales incorrectas. Verifique su correo o contraseña.")
            return redirect('home')

    return redirect('home')
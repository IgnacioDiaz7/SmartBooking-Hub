from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.mail import send_mail
from django.utils.html import strip_tags
from django.conf import settings
from django.template.loader import render_to_string 

# Llama dinámicamente al modelo de usuario activo de tu proyecto
User = get_user_model()

def home_view(request):
    """
    Renderiza la landing page principal con el modal de login y registro.
    """
    return render(request, 'users/index.html')

def registro_dueno(request):
    """
    Procesa el formulario de registro, guarda el usuario en PostgreSQL 
    y envía el correo usando tu plantilla HTML externa.
    """
    if request.method == 'POST':
        rol = request.POST.get('userRole')
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Validación básica
        if not email or not password or not nombre:
            messages.error(request, "Todos los campos del formulario son obligatorios.")
            return redirect('home')

        try:
            # Validar si el correo ya existe
            if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
                messages.error(request, "Esta dirección de correo ya se encuentra registrada.")
                return redirect('home')

            # Separar el nombre completo para guardarlo ordenadamente
            nombre_partes = nombre.split(' ', 1)
            first_name = nombre_partes[0]
            last_name = nombre_partes[1] if len(nombre_partes) > 1 else ''

            # Crear el usuario en la base de datos
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )
            user.save()

            # =========================================================
            # LÓGICA DE CORREO USANDO LA PLANTILLA EXTERNA
            # =========================================================
            asunto = 'Active su cuenta corporativa - SmartBooking HUB'
            
            
           # Variables dinámicas que viajan hacia verificacion_owner.html
            contexto_correo = {
                'nombre': nombre,
                'url_verificacion': 'http://127.0.0.1:8000/dashboard_owner.html/'
            }

            # Renderiza el archivo HTML inyectándole las variables
            mensaje_html = render_to_string('users/emails/verificacion_owner.html', contexto_correo)
            mensaje_texto = strip_tags(mensaje_html)

            # Envío de correo usando SMTP
            send_mail(
                subject=asunto,
                message=mensaje_texto,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=mensaje_html,
                fail_silently=False,
            )

            messages.success(request, f"¡Registro exitoso! Le hemos enviado un correo de confirmación a {email}.")

        except Exception as error:
            messages.error(request, f"Ocurrió un error en el servidor: {error}")

        return redirect('home')

    return redirect('home')


# ==========================================
# RUTAS DE VERIFICACIÓN Y DASHBOARD
# ==========================================

def verificar_correo(request):
    """
    Ruta intermedia que se activa al hacer clic en el botón del correo.
    Agrega un mensaje de éxito y redirige al panel de control.
    """
    messages.success(request, "¡Cuenta verificada con éxito! Bienvenido a su panel operativo.")
    return redirect('dashboard')

def dashboard(request):
    """
    Renderiza la pantalla del panel de control corporativo 
    ubicada en la app businesses.
    """
    return render(request, 'businesses/dashboard_owner.html')
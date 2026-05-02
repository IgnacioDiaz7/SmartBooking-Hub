from django.shortcuts import render
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.shortcuts import render, redirect
from django.conf import settings

def home(request):
    return render(request, 'index.html')

def dashboard_owner(request):
    
    return render(request, 'dashboard_owner.html')


def registro_dueno(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email_destino = request.POST.get('email')
        
        # Contexto para el correo
        context = {
            'nombre': nombre,
            'url_verificacion': 'http://127.0.0.1:8000/dashboard/' # URL temporal
        }
        
        # Renderizar el HTML del correo (lo crearemos en el paso 2)
        html_content = render_to_string('emails/verificacion_owner.html', context)
        text_content = strip_tags(html_content)
        
        # Configurar el correo "Luxury"
        email = EmailMultiAlternatives(
            subject='Bienvenido a la Excelencia | Verifique su cuenta',
            body=text_content,
            from_email=f'SmartBooking HUB <{settings.EMAIL_HOST_USER}>',
            to=[email_destino],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        
        return render(request, 'test.html', {'email': email_destino})
    
    return redirect('home')
from django.shortcuts import render

# --- VISTAS FRONTEND (HTML) ---
def home_view(request):
    
    return render(request, 'users/index.html')


def registro_dueno(request):
    # Aquí irá toda la lógica de validación y creación del usuario más adelante.
    # Por ahora, si alguien envía el formulario, lo mandamos a la página de éxito.
    if request.method == 'POST':
        email = request.POST.get('email', 'correo@ejemplo.com')
        return render(request, 'users/test.html', {'email': email})
    
    # Si intentan entrar por GET (escribiendo la URL), los devolvemos al inicio
    return render(request, 'users/index.html')
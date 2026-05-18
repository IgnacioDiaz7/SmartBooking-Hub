from businesses.models import Business
import logging

logger = logging.getLogger(__name__)

class TenantMiddleware:
    """
    Middleware para inyectar el contexto del 'Business' (tenant) actual en el request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        business_slug = request.headers.get('X-Business-Slug')
        
        request.business = None
        
        if business_slug:
            try:
                request.business = Business.objects.get(slug=business_slug, is_active=True)
            except Business.DoesNotExist:
                logger.warning(f"Intento de acceso a un negocio no existente o inactivo: {business_slug}")
        
        response = self.get_response(request)
        return response
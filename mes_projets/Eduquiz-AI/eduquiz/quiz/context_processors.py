from .ai_service import is_ai_enabled


def ai_status(_request):
    return {'ai_enabled': is_ai_enabled()}

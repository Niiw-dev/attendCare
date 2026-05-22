from .services import generate_missing_events


class AutoGenerateEventsMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        generate_missing_events()

        response = self.get_response(request)

        return response
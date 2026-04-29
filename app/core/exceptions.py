from rest_framework.views import exception_handler
from rest_framework.response import Response

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code in [401, 403, 404]:
            return Response(
                {"redirect": f"/no-access/?code={response.status_code}"},
                status=response.status_code
            )

    return response
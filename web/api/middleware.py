from log import logger


def defaultmiddleware(get_response):
    # One-time configuration and initialization.

    def middleware(request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        # print(f'req: {request.method} {request.path}')
        response = get_response(request)
        # print(f'res: {request.method} {request.path}')

        # Code to be executed for each request/response after
        # the view is called.

        return response

    return middleware

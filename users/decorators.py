from functools import wraps
from django.shortcuts import redirect
from django.urls import reverse
from analytics.utils import track_event


def login_required_or_redirect(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            # 🔐 Track only when redirect actually happens
            track_event(
                event_name="login_required_redirect",
                request=request,
                metadata={
                    "path": request.path
                }
            )
            return redirect(
                f"{reverse('login')}?next={request.path}"
            )

        return view_func(request, *args, **kwargs)

    return _wrapped_view

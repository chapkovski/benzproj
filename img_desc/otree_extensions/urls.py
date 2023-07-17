from django.urls import path, include, re_path
from img_desc.views import HookView
#
urlpatterns = [
    path(HookView.url_pattern, HookView.as_view(), name=HookView.url_name),
    
]


"""
URL configuration for alx_backend_graphql_crm project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# alx_backend_graphql_crm/urls.py
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView

# Try to import Playground UI, fall back to a stub so management commands don't fail.
try:
    from django_graphql_playground.views import GraphQLPlaygroundView
    playground_view = GraphQLPlaygroundView.as_view(endpoint="/graphql")
except Exception:
    from django.http import HttpResponse
    def playground_view(request):
        return HttpResponse("GraphQL Playground not available", status=503)

urlpatterns = [
    # Raw GraphQL endpoint (no UI). This never imports templates.
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=False))),
    # Optional UI (safe fallback if package missing)
    path("graphiql", playground_view),
]
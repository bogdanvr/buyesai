from rest_framework import generics

from integrations.llm_serializers import LlmProviderAccountSerializer
from integrations.models import LlmProviderAccount


class LlmProviderAccountListCreateAPIView(generics.ListCreateAPIView):
    serializer_class = LlmProviderAccountSerializer
    queryset = LlmProviderAccount.objects.all().order_by("priority", "name", "id")


class LlmProviderAccountDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = LlmProviderAccountSerializer
    queryset = LlmProviderAccount.objects.all()

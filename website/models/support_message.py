from django.db import models


class SupportMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, default='')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Mensagem de Suporte"
        verbose_name_plural = "Mensagens de Suporte"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"

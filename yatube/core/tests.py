from django.test import Client, TestCase


class Err404Tests(TestCase):
    def setUp(self):
        # Создаем неавторизованый клиент
        self.guest_client = Client()

    def test_url_use_correct_template(self):
        """Проверка открытия шаблона с ошибкой при отсутствии страницы."""
        template = 'core/404.html'
        response = self.guest_client.get('notExistPage/')
        self.assertTemplateUsed(response, template)

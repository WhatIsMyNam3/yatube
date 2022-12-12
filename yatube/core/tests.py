from django.test import Client, TestCase


class Err404Tests(TestCase):
    def setUp(self):
        # Создаем неавторизованый клиент
        self.guest_client = Client()

    def test_404_use_correct_template(self):
        """Проверка открытия шаблона с ошибкой при отсутствии страницы."""
        template = 'core/404.html'
        response = self.guest_client.get('notExistPage/')
        self.assertTemplateUsed(response, template)

    def test_403_use_correct_template(self):
        """Проверка открытия шаблона с ошибкой при отсутствии страницы."""
        template = 'core/403csrf.html'
        response = self.guest_client.get()
        self.assertTemplateUsed(response, template)

    def test_500_use_correct_template(self):
        """Проверка открытия шаблона с ошибкой при отсутствии страницы."""
        template = 'core/403csrf.html'
        response = self.guest_client.get()
        self.assertTemplateUsed(response, template)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 500)
        self.assertTemplateUsed(response, 'core/500.html')

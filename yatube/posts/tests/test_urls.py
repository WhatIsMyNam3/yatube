from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from http import HTTPStatus
from django.core.cache import cache

from ..models import Group, Post

User = get_user_model()


class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
        )

    def setUp(self) -> None:
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(PostsURLTests.user)
        self.user1 = User.objects.create_user(username='new_auth')
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user1)
        cache.clear()

    def test_urls_exist_for_guests(self):
        """Проверка на доступность страниц гостю."""
        url_names = [
            '/',
            f'/group/{self.group.slug}/',
            f'/profile/{self.post.author}/',
            f'/posts/{self.post.pk}/',
        ]
        for address in url_names:
            with self.subTest():
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_correct_templates(self):
        """URL-адрес использует соответствующий шаблон."""
        url_templates_names = {
            '/': 'posts/index.html',
            f'/group/{self.group.slug}/': 'posts/group_list.html',
            f'/profile/{self.post.author}/': 'posts/profile.html',
            f'/posts/{self.post.id}/': 'posts/post_detail.html',
            f'/posts/{self.post.id}/edit/': 'posts/create_post.html',
            '/create/': 'posts/create_post.html',
        }
        for address, template in url_templates_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)

    def test_posts_post_id_edit_url_exists_author(self):
        """Страница /posts/post_id/edit/ доступна только автору."""
        response = self.authorized_client.get(f"/posts/{self.post.id}/edit/")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_url_redirect_anonymous_on_auth_login(self):
        """Страница posts/post_id/edit редиректит гостя на страницу
        регистрации.
        """
        response = self.guest_client.get(
            f'/posts/{self.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/edit/'
        )

    def test_post_edit_url_redirect_authorized_on_post_detail(self):
        """Страница posts/post_id/edit редиректит зарегистрированного
         пользователя на страницу поста.
        """
        response = self.authorized_client2.get(
            f'/posts/{self.post.id}/edit/',
            follow=True
        )
        self.assertRedirects(
            response,
            f'/posts/{self.post.id}/'
        )

    def test_create_url_redirect_anonymous_on_auth_login(self):
        """Страница /create/ редиректит гостя на страницу регистрации."""
        response = self.guest_client.get('/create/', follow=True)
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_not_exists_url(self):
        """Проверка несуществующего URL."""
        response = self.guest_client.get('/top100posts/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_anonymous_cannot_commen(self):
        """Неавторизированный пользователь не может комментаровать."""
        response = self.guest_client.get(f'/posts/{self.post.id}/comment/')
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{self.post.id}/comment/'
        )

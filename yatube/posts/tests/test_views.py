import shutil
import tempfile
from django import forms
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.cache import cache
from django.conf import settings
from django.test import Client, TestCase
from django.core.files.uploadedfile import SimpleUploadedFile

from ..models import Group, Post, Follow, Comment

User = get_user_model()
NUMBER_POSTS_PER_PAGE = 10
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PostsViewsTests(TestCase):
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
            group=cls.group,
        )
        cls.user1 = User.objects.create_user(username='new_auth')
        cls.group1 = Group.objects.create(
            title='Тестовая группа1',
            slug='test_slug1',
            description='Тестовое описание',
        )
        cls.post1 = Post.objects.create(
            author=cls.user1,
            text='Тестовый пост1',
            group=cls.group1,
        )
        cls.follow = Follow.objects.create(
            user=cls.user,
            author=cls.user1
        )

    def setUp(self) -> None:
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse(
                'posts:group_list', kwargs={'slug': f'{self.group.slug}'}
            ): 'posts/group_list.html',
            reverse(
                'posts:profile', kwargs={'username': f'{self.post.author}'}
            ): 'posts/profile.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse(
                "posts:post_edit", kwargs={'post_id': self.post.id}
            ): "posts/create_post.html",
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            ): 'posts/post_detail.html',
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        expected = list(Post.objects.all()[:NUMBER_POSTS_PER_PAGE])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_group_list_show_correct_context(self):
        """Список постов в шаблоне group_list равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse('posts:group_list', kwargs={'slug': self.group.slug})
        )
        expected = list(Post.objects.filter(
            group_id=self.group.id)[:NUMBER_POSTS_PER_PAGE])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_profile_show_correct_context(self):
        """Список постов в шаблоне profile равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse(
                'posts:profile', kwargs={'username': f'{self.post.author}'}
            )
        )
        expected = list(Post.objects.filter(
            author_id=self.user.id)[:NUMBER_POSTS_PER_PAGE])
        self.assertEqual(list(response.context['page_obj']), expected)

    def test_post_detail_show_correct_context(self):
        """Список постов в шаблоне post_detail равен ожидаемому контексту."""
        response = self.guest_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(response.context.get('post').text, self.post.text)
        self.assertEqual(response.context.get('post').author, self.post.author)
        self.assertEqual(response.context.get('post').group, self.post.group)

    def test_post_edit_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_post_create_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_create')
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_check_group_in_pages(self):
        """Проверяем создание поста на страницах с выбранной группой"""
        form_fields = {
            reverse('posts:index'): Post.objects.get(group=self.post.group),
            reverse(
                'posts:group_list', kwargs={'slug': self.group.slug}
            ): Post.objects.get(group=self.post.group),
            reverse(
                'posts:profile', kwargs={'username': self.post.author}
            ): Post.objects.get(group=self.post.group),
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                response = self.authorized_client.get(value)
                form_field = response.context['page_obj']
                self.assertIn(expected, form_field)

    def test_check_group_not_in_mistake_group_list_page(self):
        """Проверяем чтобы созданный Пост с группой не попап в чужую группу."""
        value = reverse(
            'posts:group_list',
            kwargs={'slug': self.group.slug}
        )
        expected = Post.objects.get(group=self.post1.group)
        response = self.authorized_client.get(value)
        form_field = response.context['page_obj']
        self.assertNotIn(expected, form_field)

    def test_authorized_user_add_comment(self):
        """Добавление коммента авторизованным пользователем"""
        comment = Comment.objects.create(
            post=self.post,
            author=self.user,
            text='Коммент'
        )
        response = self.authorized_client.get(f'/posts/{self.post.id}/')
        self.assertEqual(response.context.get('comments')[0], comment)

    def test_cache_index(self):
        """Тест кеша страницы index."""
        response = self.authorized_client.get(reverse('posts:index'))
        first_cache = response.content
        post = Post.objects.get(id=self.post.pk)
        post.delete()
        response = self.authorized_client.get(reverse('posts:index'))
        second_cache = response.content
        self.assertEqual(first_cache, second_cache)
        cache.clear()
        response = self.authorized_client.get(reverse('posts:index'))
        third_cache = response.context['page_obj']
        self.assertNotIn(post, third_cache)

    def test_new_post_follow_index_show_correct_context(self):
        """Шаблон follow_index сформирован с правильным контекстом."""

        test_post = Post.objects.create(
            text='Тестовый пост1',
            author=self.user
        )
        expected = test_post.text
        response = self.authorized_client.get(reverse('posts:follow_index'))
        first_post = response.context['page_obj'].object_list[0]
        self.assertEqual(first_post.text, expected)

        self.authorized_client.get(reverse('posts:profile_unfollow',
                                           kwargs={'username': self.user1}))

        response = self.authorized_client.get(reverse('posts:follow_index'))
        self.assertFalse(len(response.context.get('page_obj').object_list))

    def test_follow_another_user(self):
        """Follow на другого пользователя работает корректно"""
        self.authorized_client.get(reverse('posts:profile_follow',
                                           kwargs={'username': self.user1}))
        follow_exist = Follow.objects.filter(user=self.user,
                                             author=self.user1).exists()
        self.assertTrue(follow_exist)

    def test_unfollow_another_user(self):
        """Unfollow от другого пользователя работает корректно"""
        Follow.objects.create(
            user=self.user,
            author=self.user1
        )
        self.authorized_client.get(reverse('posts:profile_unfollow',
                                           kwargs={'username': self.user1}))
        follow_exist = Follow.objects.filter(user=self.user,
                                             author=self.user1).exists()
        self.assertFalse(follow_exist)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.author = User.objects.create_user(username='test_name')
        cls.group = Group.objects.create(
            title=('Заголовок для тестовой группы'),
            slug='test_slug',
            description='Тестовое описание')
        cls.posts = []
        for i in range(13):
            cls.posts.append(Post(
                text=f'Тестовый пост {i}',
                author=cls.author,
                group=cls.group
            )
            )
        cache.clear()
        Post.objects.bulk_create(cls.posts)

    def test_first_page_contains_ten_records(self):
        """Проверка работы пагинатора для 1ой страницы index."""
        page_list = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.author}),
        ]
        for page in page_list:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    NUMBER_POSTS_PER_PAGE)

    def test_second_page_contains_three_records(self):
        """Проверка работы пагинатора для 2ой страницы index."""
        page_list = [
            reverse('posts:index') + '?page=2',
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2',
            reverse('posts:profile',
                    kwargs={'username': self.author}) + '?page=2',
        ]
        for page in page_list:
            with self.subTest(page=page):
                response = self.client.get(page)
                self.assertEqual(
                    len(response.context['page_obj']),
                    3)


class ImageTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self) -> None:
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        cache.clear()

    def test_image_in_templates(self):
        """Проверяем чтобы картинка передавалась в шалоны."""
        templates = (
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse(
                'posts:profile', kwargs={'username': f'{self.post.author}'}
            )
        )
        for url in templates:
            with self.subTest(url):
                response = self.guest_client.get(url)
                obj = response.context['page_obj'][0]
                self.assertEqual(obj.image, self.post.image)

    def test_image_in_post_detail(self):
        """Проверяем чтобы картинка передавалась на post_detail."""
        response = self.guest_client.get(
            reverse(
                'posts:post_detail', kwargs={'post_id': self.post.id}
            )
        )
        self.assertEqual(response.context.get('post').image, self.post.image)

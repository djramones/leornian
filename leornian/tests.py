from django.test import TestCase


class BasicTests(TestCase):
    def test_basic_site_views_get(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/accounts/me/")
        self.assertRedirects(response, "/accounts/login/?next=/accounts/me/")

        # Admin views
        response = self.client.get("/admin/")
        self.assertRedirects(response, "/admin/login/?next=/admin/")

        # Auth views
        response = self.client.get("/accounts/login/")
        self.assertEqual(response.status_code, 200)
        response = self.client.get("/accounts/logout/")
        self.assertRedirects(response, "/")

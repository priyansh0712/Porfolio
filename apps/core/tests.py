"""
Core App Unit Tests — Application Rate Limiter & Utility Tests.
"""
from django.core.cache import cache
from django.test import TestCase, RequestFactory
from django.http import HttpResponse

from apps.core.ratelimit import rate_limit, get_client_ip


class RateLimitTest(TestCase):
    """Tests for rate_limit decorator functionality."""

    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def test_get_client_ip_forwarded_for(self):
        """Should extract IP from HTTP_X_FORWARDED_FOR header."""
        request = self.factory.get('/', HTTP_X_FORWARDED_FOR='203.0.113.195, 70.41.3.18')
        ip = get_client_ip(request)
        self.assertEqual(ip, '203.0.113.195')

    def test_rate_limit_exceeded_returns_429(self):
        """Requests exceeding threshold within window should return 429 status code."""
        @rate_limit(key_prefix='test', limit=3, period_seconds=60)
        def dummy_view(request):
            return HttpResponse("OK")

        request = self.factory.get('/')
        request.META['REMOTE_ADDR'] = '198.51.100.1'

        # First 3 requests should pass
        for _ in range(3):
            response = dummy_view(request)
            self.assertEqual(response.status_code, 200)

        # 4th request should trigger 429 Too Many Requests
        response_4th = dummy_view(request)
        self.assertEqual(response_4th.status_code, 429)

    def test_rate_limit_methods_filtering(self):
        """When methods=['POST'] is specified, GET requests should not be rate-limited."""
        @rate_limit(key_prefix='test_methods', limit=2, period_seconds=60, methods=['POST'])
        def dummy_view(request):
            return HttpResponse("OK")

        get_request = self.factory.get('/')
        get_request.META['REMOTE_ADDR'] = '198.51.100.2'

        # 5 GET requests should all succeed
        for _ in range(5):
            res = dummy_view(get_request)
            self.assertEqual(res.status_code, 200)

        post_request = self.factory.post('/')
        post_request.META['REMOTE_ADDR'] = '198.51.100.2'

        # First 2 POSTs should pass
        self.assertEqual(dummy_view(post_request).status_code, 200)
        self.assertEqual(dummy_view(post_request).status_code, 200)

        # 3rd POST exceeds limit -> 429
        self.assertEqual(dummy_view(post_request).status_code, 429)


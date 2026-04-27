from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.halls.models import Hall
from apps.movies.models import AgeRating, Movie, MovieGenre
from apps.pricing.models import TicketCurrency, TicketPrice
from apps.screenings.models import MovieSession


class MovieApiTests(APITestCase):
    def setUp(self):
        self.movie = Movie.objects.create(
            title='Dune: Part Two',
            description='Epic sci-fi saga.',
            genre=MovieGenre.SCI_FI,
            duration=166,
            age_rating=AgeRating.AGE_12,
            poster_url='https://example.com/dune-2.jpg',
            release_date=timezone.now().date(),
            is_active=True,
        )
        self.other_movie = Movie.objects.create(
            title='The Grand Comedy',
            description='Comedy feature.',
            genre=MovieGenre.COMEDY,
            duration=102,
            age_rating=AgeRating.AGE_12,
            poster_url='https://example.com/comedy.jpg',
            release_date=timezone.now().date(),
            is_active=True,
        )
        self.inactive_movie = Movie.objects.create(
            title='Hidden Movie',
            description='Should not be returned.',
            genre=MovieGenre.DRAMA,
            duration=99,
            age_rating=AgeRating.AGE_16,
            poster_url='https://example.com/hidden.jpg',
            release_date=timezone.now().date(),
            is_active=False,
        )
        hall = Hall.objects.create(name='Movie API Hall', rows=5, seats_per_row=6)
        future_start = timezone.now() + timedelta(days=1)
        past_start = timezone.now() - timedelta(days=1)

        self.future_session = MovieSession.objects.create(
            movie=self.movie,
            hall=hall,
            start_datetime=future_start,
            end_datetime=future_start + timedelta(hours=3),
            is_active=True,
        )
        TicketPrice.objects.create(
            session=self.future_session,
            amount='450.00',
            currency=TicketCurrency.KGS,
        )
        self.past_session = MovieSession.objects.create(
            movie=self.movie,
            hall=hall,
            start_datetime=past_start,
            end_datetime=past_start + timedelta(hours=3),
            is_active=True,
        )
        TicketPrice.objects.create(
            session=self.past_session,
            amount='430.00',
            currency=TicketCurrency.KGS,
        )
        self.inactive_session = MovieSession.objects.create(
            movie=self.movie,
            hall=hall,
            start_datetime=future_start + timedelta(days=1),
            end_datetime=future_start + timedelta(days=1, hours=3),
            is_active=False,
        )
        TicketPrice.objects.create(
            session=self.inactive_session,
            amount='470.00',
            currency=TicketCurrency.KGS,
        )

    def test_movies_list_returns_paginated_active_movies_and_supports_filters(self):
        response = self.client.get(
            '/api/v1/movies/',
            {
                'genre': MovieGenre.SCI_FI,
                'search': 'dune',
                'page': 1,
                'page_size': 20,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 1)
        self.assertIsNone(response.data['next'])
        self.assertIsNone(response.data['previous'])
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], self.movie.title)

    def test_movie_detail_returns_future_active_sessions_only(self):
        response = self.client.get(f'/api/v1/movies/{self.movie.id}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], self.movie.id)
        self.assertEqual(len(response.data['sessions']), 1)
        self.assertEqual(response.data['sessions'][0]['id'], self.future_session.id)
        self.assertEqual(response.data['sessions'][0]['price']['currency'], 'KGS')

    def test_movie_detail_returns_not_found_for_inactive_movie(self):
        response = self.client.get(f'/api/v1/movies/{self.inactive_movie.id}/')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data['error'], 'NOT_FOUND')
        self.assertEqual(response.data['message'], 'Фильм не найден')

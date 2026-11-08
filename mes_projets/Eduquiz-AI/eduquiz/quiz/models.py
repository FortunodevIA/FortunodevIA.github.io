from collections import Counter
import os
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

LEVEL_CHOICES = [
    ('easy', 'Facile'),
    ('medium', 'Moyen'),
    ('hard', 'Difficile'),
]
OPTION_CHOICES = [
    ('a', 'A'),
    ('b', 'B'),
    ('c', 'C'),
    ('d', 'D'),
]


def document_upload_path(instance, filename):
    safe_name = os.path.basename(filename)
    unique_prefix = uuid.uuid4().hex[:8]
    return f'documents/user_{instance.user_id}/{unique_prefix}_{safe_name}'


class Document(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='documents',
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_upload_path)
    extracted_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    keywords = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)

    def keyword_list(self):
        return [kw.strip() for kw in self.keywords.split(',') if kw.strip()]

    def short_summary(self):
        return self.summary if len(self.summary) < 260 else self.summary[:256].rstrip() + '...'

    def __str__(self):
        return self.title

    class Meta:
        indexes = [
            models.Index(fields=['user', '-uploaded_at']),
        ]


class Quiz(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='quizzes',
    )
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='quizzes',
    )
    title = models.CharField(max_length=255, default='Quiz généré')
    question_count = models.PositiveSmallIntegerField(default=10)
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='easy')
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.title} — {self.document.title}"

    class Meta:
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]


class QuizQuestion(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    QUESTION_TYPE_CHOICES = [
        ('mcq', 'Choix unique'),
        ('tf', 'Vrai / Faux'),
        ('multi', 'Choix multiple'),
    ]
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES, default='mcq')
    # `correct_option` kept for backward compat; `correct_options` stores comma-separated keys for multi
    correct_option = models.CharField(max_length=1, choices=OPTION_CHOICES, blank=True)
    correct_options = models.CharField(max_length=32, blank=True)
    explanation = models.TextField(blank=True)

    def all_options(self):
        return [
            ('a', self.option_a),
            ('b', self.option_b),
            ('c', self.option_c),
            ('d', self.option_d),
        ]

    def correct_text(self):
        if self.question_type == 'multi' and self.correct_options:
            keys = [k.strip() for k in self.correct_options.split(',') if k.strip()]
            opts = dict(self.all_options())
            return ', '.join([opts.get(k, '') for k in keys])
        return dict(self.all_options()).get(self.correct_option, '')

    def __str__(self):
        return self.text[:80]


class QuizAttempt(models.Model):
    quiz = models.ForeignKey(
        Quiz,
        on_delete=models.CASCADE,
        related_name='attempts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='attempts',
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.PositiveSmallIntegerField(default=0)
    max_score = models.PositiveSmallIntegerField(default=0)
    feedback = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.quiz.title} ({self.score}/{self.max_score})"

    @property
    def duration_seconds(self):
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    @property
    def duration_display(self):
        seconds = self.duration_seconds
        if seconds is None:
            return '—'
        minutes, remainder = divmod(seconds, 60)
        return f"{minutes}m {remainder}s" if minutes else f"{remainder}s"

    class Meta:
        indexes = [
            models.Index(fields=['user', '-started_at']),
        ]


class Answer(models.Model):
    attempt = models.ForeignKey(
        QuizAttempt,
        on_delete=models.CASCADE,
        related_name='answers',
    )
    question = models.ForeignKey(QuizQuestion, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, choices=OPTION_CHOICES)
    is_correct = models.BooleanField(default=False)

    def selected_text(self):
        return dict(self.question.all_options()).get(self.selected_option, '')

    def __str__(self):
        return f"{self.question.text[:60]} — {self.selected_option}"
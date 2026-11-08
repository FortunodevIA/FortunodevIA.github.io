import io
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from .models import Document, Quiz
from .rag_generator import _build_mcq_from_candidates
from .utils import _clean_extracted_pdf_text, extract_pdf_text, generate_quiz_questions


class QuizAppBasicsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.client = Client()
        self.client.login(username='testuser', password='testpass')

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('quiz:dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_document_upload_rejects_non_pdf(self):
        response = self.client.post(
            reverse('quiz:dashboard'),
            {
                'title': 'Test',
                'file': SimpleUploadedFile('test.txt', b'This is not a PDF', content_type='text/plain'),
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Seuls les fichiers PDF sont acceptés.')

    def test_quiz_title_generated_from_document(self):
        document = Document.objects.create(
            user=self.user,
            title='Cours Test',
            file='documents/user_1/test.pdf',
            extracted_text=(
                "L'architecture d'une application web comprend le serveur, le client, et la base de données. "
                'Un serveur HTTP répond aux requêtes et envoie des pages HTML. '
                "Le concept de session permet de maintenir l'état. "
                'Les données sont souvent stockées dans une base relationnelle. '
                "La sécurité se gère avec l'authentification et l'autorisation."
            ),
        )
        response = self.client.post(
            reverse('quiz:create_quiz', args=[document.id]),
            {'question_count': '5', 'level': 'easy'},
        )
        self.assertEqual(response.status_code, 302)
        quiz = Quiz.objects.filter(document=document).first()
        self.assertIsNotNone(quiz)
        self.assertTrue(quiz.title.startswith('Quiz : Cours Test'))

    def test_generate_quiz_questions_fallback(self):
        text = (
            "L'architecture d'une application web comprend le serveur, le client, et la base de données. "
            'Un serveur HTTP répond aux requêtes et envoie des pages HTML. '
            "Le concept de session permet de maintenir l'état. "
            'Les données sont souvent stockées dans une base relationnelle. '
            "La sécurité se gère avec l'authentification et l'autorisation."
        )
        questions = generate_quiz_questions(text, count=5, level='easy', mode='default')
        self.assertEqual(len(questions), 5)
        for q in questions:
            self.assertIn('text', q)
            self.assertIn('options', q)
            self.assertEqual(len(q['options']), 4)
            self.assertIn(q['correct'], {'a', 'b', 'c', 'd'})

    @patch('eduquiz.quiz.views.generate_questions_offline_from_text')
    @patch('eduquiz.quiz.views.extract_pdf_text')
    def test_dashboard_skips_malformed_generated_questions(self, mock_extract_text, mock_generate):
        mock_extract_text.return_value = (
            'Les modèles Probit et Logit sont utilisés pour expliquer des variables dépendantes binaires. '
            'La probabilité de succès est notée Pr(xik = 1|Xi) = Φ(Xiβ). '
            'Le modèle logit repose sur la fonction logistique.'
        )
        mock_generate.return_value = [
            {'text': 'Question valide', 'options': ['Oui', 'Non', 'Peut-être', 'Aucune idée'], 'correct': 'a', 'explanation': 'Oui', 'question_type': 'mcq'},
            {'text': 'Question cassée', 'options': ['Seulement 1'], 'correct': 'a', 'explanation': 'Bad', 'question_type': 'mcq'},
            {'text': 'Question invalide', 'options': ['A', 'B', 'C', 'D'], 'correct': 'z', 'explanation': 'Bad', 'question_type': 'mcq'},
        ]
        pdf = SimpleUploadedFile(
            'math.pdf',
            b'%PDF-1.4\n% valid-ish PDF bytes\n%%EOF',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('quiz:dashboard'),
            {'title': 'Cours math', 'file': pdf},
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Quiz.objects.filter(user=self.user).exists())

    @patch('random.random', side_effect=[0.20, 0.40, 0.75, 0.90, 0.30])
    def test_question_type_ratio_prefers_tf_and_multi(self, _mock_random):
        candidates = ['alpha', 'beta', 'gamma', 'delta', 'epsilon']
        questions = _build_mcq_from_candidates(candidates, 5, full_text=' '.join(candidates))
        self.assertEqual([q['question_type'] for q in questions[:3]], ['tf', 'multi', 'mcq'])

    def test_generated_question_text_is_clean(self):
        candidates = ['alpha', 'beta', 'gamma', 'delta', 'epsilon']
        questions = _build_mcq_from_candidates(candidates, 3, full_text='alpha beta gamma delta epsilon')
        for q in questions:
            self.assertNotIn('Paraphrase', q['text'])
            self.assertNotIn('Selon le texte', q['text'])
            self.assertNotIn('###', q['text'])

    def test_math_context_text_is_not_rejected_as_formula_noise(self):
        text = (
            'Les modèles Probit et Logit sont utilisés pour expliquer des variables dépendantes binaires. '
            'La probabilité de succès est notée Pr(Y = 1|X) = Φ(Xβ). '
            'Le modèle logit repose sur la fonction logistique et permet de mesurer l’effet d’une variable explicative.'
        )
        cleaned = _clean_extracted_pdf_text(text)
        self.assertIn('modèles Probit et Logit', cleaned)
        self.assertIn('fonction logistique', cleaned.lower())
        self.assertGreater(len(cleaned), 60)

    @patch('eduquiz.quiz.views.extract_pdf_text')
    def test_dashboard_accepts_short_valid_math_text(self, mock_extract_text):
        mock_extract_text.return_value = 'Les modèles Probit et Logit sont expliqués dans ce cours.'
        pdf = SimpleUploadedFile(
            'short_math.pdf',
            b'%PDF-1.4\n% valid-ish PDF bytes\n%%EOF',
            content_type='application/pdf',
        )

        response = self.client.post(
            reverse('quiz:dashboard'),
            {'title': 'Cours math court', 'file': pdf},
        )

        self.assertEqual(response.status_code, 302)

    def test_generate_quiz_questions_includes_all_question_types(self):
        text = (
            'La probabilité d’un événement est la mesure de sa fréquence. '
            'Un modèle probit relie une variable latente à des variables explicatives. '
            'La fonction de répartition est symétrique autour de zéro. '
            'Le gradient de la log-vraisemblance dépend du produit de la densité et des variables explicatives. '
            'Une question à choix multiple peut avoir plusieurs bonnes réponses.'
        )
        with patch('random.random', side_effect=[0.05, 0.60, 0.90, 0.20, 0.35, 0.80]):
            questions = generate_quiz_questions(text, count=6, level='easy', mode='default')
        self.assertGreaterEqual(len(questions), 4)
        q_types = {q.get('question_type', 'mcq') for q in questions}
        self.assertTrue({'tf', 'multi', 'mcq'}.issubset(q_types))
        for q in questions:
            self.assertNotIn('Paraphrase', q.get('text', ''))
            self.assertNotIn('Selon le texte', q.get('text', ''))
            self.assertNotIn('###', q.get('text', ''))

    def test_review_page_does_not_offer_manual_question_type_choice(self):
        document = Document.objects.create(
            user=self.user,
            title='Cours Test',
            file='documents/user_1/test.pdf',
            extracted_text='Le cours contient des notions pratiques et des définitions utiles.',
        )
        quiz = Quiz.objects.create(
            user=self.user,
            document=document,
            title='Quiz : Cours Test',
            question_count=2,
            is_published=False,
        )
        quiz.questions.create(
            text='Le cours est utile ?',
            option_a='Oui',
            option_b='Non',
            option_c='Peut-être',
            option_d='Aucune idée',
            correct_option='a',
            question_type='mcq',
            explanation='Le cours est utile.',
        )
        response = self.client.get(reverse('quiz:review_quiz', args=[quiz.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="type_')
        self.assertNotContains(response, 'Choix unique')
        self.assertNotContains(response, 'Vrai / Faux')
        self.assertNotContains(response, 'Choix multiple')

    def test_math_noise_is_filtered_from_generated_questions(self):
        text = (
            'Les modèles Probit et Logit sont utilisés pour les variables dépendantes binaires. '
            'La probabilité de succès est notée Pr(xik = 1|Xi) = Φ(Xiβ). '
            'On mesure l’impact moyen d’une variable xk sur la probabilité. '
            'Le modèle logit repose sur la fonction logistique. '
            'Le paramètre β capture l’effet de chaque variable explicative.'
        )
        questions = generate_quiz_questions(text, count=4, level='easy', mode='default')
        self.assertTrue(questions)
        rendered = ' '.join(q.get('text', '') for q in questions)
        self.assertNotIn('xik', rendered.lower())
        self.assertNotIn('probabilité de succès est notée pr', rendered.lower())
        self.assertNotIn('phi', rendered.lower())
        for q in questions:
            self.assertNotIn('###', q.get('text', ''))
            self.assertNotIn('xik', q.get('text', '').lower())


class UtilsTest(TestCase):
    def test_extract_pdf_text_returns_string(self):
        sample_pdf = io.BytesIO(
            b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 44 >>\nstream\nBT /F1 24 Tf 72 712 Td (Hello PDF) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000010 00000 n \n0000000067 00000 n \n0000000116 00000 n \n0000000231 00000 n \ntrailer\n<< /Root 1 0 R /Size 5 >>\nstartxref\n333\n%%EOF'
        )
        text = extract_pdf_text(sample_pdf)
        self.assertIsInstance(text, str)

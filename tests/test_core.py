"""
Tests unitaires pour le module core
"""

import unittest
import numpy as np
import os
import sys

# Ajouter le chemin du projet
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFaceDetector(unittest.TestCase):
    """Tests pour FaceDetector"""

    def test_import(self):
        """Test d'import du module"""
        from src.core.face_detector import FaceDetector, FaceData
        self.assertIsNotNone(FaceDetector)
        self.assertIsNotNone(FaceData)

    def test_boundary_points(self):
        """Test de génération des points de bordure"""
        from src.core.face_detector import FaceDetector

        detector = FaceDetector()
        shape = (480, 640, 3)  # h, w, c
        points = detector._get_boundary_points(shape)

        self.assertEqual(len(points), 8)
        self.assertEqual(points.shape, (8, 2))

    def test_landmark_constants(self):
        """Test des constantes de landmarks"""
        from src.core.face_detector import FaceDetector

        self.assertEqual(len(FaceDetector.JAW_POINTS), 17)
        self.assertEqual(len(FaceDetector.RIGHT_EYE_POINTS), 6)
        self.assertEqual(len(FaceDetector.LEFT_EYE_POINTS), 6)
        self.assertEqual(len(FaceDetector.NOSE_POINTS), 8)


class TestFaceMorpher(unittest.TestCase):
    """Tests pour FaceMorpher"""

    def test_import(self):
        """Test d'import du module"""
        from src.core.face_morpher import FaceMorpher
        self.assertIsNotNone(FaceMorpher)

    def test_triangulation(self):
        """Test de triangulation de Delaunay"""
        from src.core.face_morpher import FaceMorpher

        morpher = FaceMorpher()

        # Points simples
        points = np.array([
            [0, 0], [100, 0], [100, 100], [0, 100], [50, 50]
        ], dtype=np.float64)

        triangulation = morpher.compute_triangulation(points)
        self.assertIsNotNone(triangulation)
        self.assertTrue(len(triangulation) > 0)

    def test_cross_dissolve(self):
        """Test de dissolution croisée"""
        from src.core.face_morpher import FaceMorpher

        morpher = FaceMorpher()

        # Créer deux images de test
        im1 = np.zeros((100, 100, 3), dtype=np.uint8)
        im2 = np.ones((100, 100, 3), dtype=np.uint8) * 255

        frames = morpher.cross_dissolve(im1, im2, 5)

        self.assertEqual(len(frames), 5)
        self.assertEqual(frames[0].shape, (100, 100, 3))


class TestVideoEncoder(unittest.TestCase):
    """Tests pour VideoEncoder"""

    def test_import(self):
        """Test d'import du module"""
        from src.core.video_encoder import VideoEncoder
        self.assertIsNotNone(VideoEncoder)

    def test_check_ffmpeg(self):
        """Test de vérification FFmpeg"""
        from src.core.video_encoder import VideoEncoder

        encoder = VideoEncoder()
        # Ne pas échouer si FFmpeg n'est pas installé
        result = encoder.check_ffmpeg()
        self.assertIsInstance(result, bool)


class TestFaceAligner(unittest.TestCase):
    """Tests pour FaceAligner"""

    def test_import(self):
        """Test d'import du module"""
        from src.core.face_aligner import FaceAligner
        self.assertIsNotNone(FaceAligner)

    def test_transformation(self):
        """Test du calcul de transformation"""
        from src.core.face_aligner import FaceAligner

        aligner = FaceAligner()

        # Points identiques -> transformation identité
        points = np.array([
            [10, 10], [20, 10], [20, 20], [10, 20]
        ], dtype=np.float64)

        M = aligner._compute_transformation(points, points)

        # La transformation devrait être proche de l'identité
        self.assertEqual(M.shape, (3, 3))


if __name__ == '__main__':
    unittest.main()

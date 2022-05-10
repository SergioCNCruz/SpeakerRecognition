import os
import torch
import unittest
import numpy as np

import feature_extraction
import neural_net
import evaluation
import myconfig


class TestFeatureExtraction(unittest.TestCase):
    def setUp(self):
        self.spk_to_utts = feature_extraction.get_spk_to_utts(
            myconfig.TEST_DATA_DIR)

    def test_extract_features(self):
        features = feature_extraction.extract_features(os.path.join(
            myconfig.TEST_DATA_DIR, "61/70968/61-70968-0000.flac"))
        self.assertEqual(features.shape, (154, myconfig.N_MFCC))

    def test_extract_sliding_windows(self):
        features = feature_extraction.extract_features(os.path.join(
            myconfig.TEST_DATA_DIR, "61/70968/61-70968-0000.flac"))
        sliding_windows = feature_extraction.extract_sliding_windows(features)
        self.assertEqual(len(sliding_windows), 2)
        self.assertEqual(sliding_windows[0].shape,
                         (myconfig.SEQ_LEN, myconfig.N_MFCC))

    def test_get_spk_to_utts(self):
        self.assertEqual(len(self.spk_to_utts.keys()), myconfig.N_MFCC)
        self.assertEqual(len(self.spk_to_utts["121"]), 62)

    def test_get_triplet(self):
        anchor1, pos1, neg1 = feature_extraction.get_triplet(self.spk_to_utts)
        anchor1_spk = os.path.basename(anchor1).split("-")[0]
        pos1_spk = os.path.basename(pos1).split("-")[0]
        neg1_spk = os.path.basename(neg1).split("-")[0]
        self.assertEqual(anchor1_spk, pos1_spk)
        self.assertNotEqual(anchor1_spk, neg1_spk)

        anchor2, pos2, neg2 = feature_extraction.get_triplet(self.spk_to_utts)
        anchor2_spk = os.path.basename(anchor2).split("-")[0]
        pos2_spk = os.path.basename(pos2).split("-")[0]
        neg2_spk = os.path.basename(neg2).split("-")[0]
        self.assertNotEqual(anchor1_spk, anchor2_spk)
        self.assertNotEqual(pos1_spk, pos2_spk)
        self.assertNotEqual(neg1_spk, neg2_spk)

    def test_get_triplet_features(self):
        anchor, pos, neg = feature_extraction.get_triplet_features(
            self.spk_to_utts)
        self.assertEqual(myconfig.N_MFCC, anchor.shape[1])
        self.assertEqual(myconfig.N_MFCC, pos.shape[1])
        self.assertEqual(myconfig.N_MFCC, neg.shape[1])

    def test_get_triplet_features_trimmed(self):
        anchor, pos, neg = feature_extraction.get_triplet_features_trimmed(
            self.spk_to_utts)
        self.assertEqual(anchor.shape, (myconfig.SEQ_LEN, myconfig.N_MFCC))
        self.assertEqual(pos.shape, (myconfig.SEQ_LEN, myconfig.N_MFCC))
        self.assertEqual(neg.shape, (myconfig.SEQ_LEN, myconfig.N_MFCC))

    def test_get_batched_triplet_input(self):
        batch_input = feature_extraction.get_batched_triplet_input(
            self.spk_to_utts, batch_size=4)
        self.assertEqual(batch_input.shape, torch.Size(
            [3 * 4, myconfig.SEQ_LEN, myconfig.N_MFCC]))


class TestNeuralNet(unittest.TestCase):

    def test_get_triplet_loss1(self):
        anchor = torch.tensor([0.0, 1.0])
        pos = torch.tensor([0.0, 1.0])
        neg = torch.tensor([0.0, 1.0])
        loss = neural_net.get_triplet_loss(anchor, pos, neg)
        loss_value = loss.data.numpy().item()
        self.assertAlmostEqual(loss_value, myconfig.TRIPLET_ALPHA)

    def test_get_triplet_loss2(self):
        anchor = torch.tensor([0.6, 0.8])
        pos = torch.tensor([0.6, 0.8])
        neg = torch.tensor([-0.8, 0.6])
        loss = neural_net.get_triplet_loss(anchor, pos, neg)
        loss_value = loss.data.numpy().item()
        self.assertAlmostEqual(loss_value, 0)

    def test_get_triplet_loss2(self):
        anchor = torch.tensor([0.6, 0.8])
        pos = torch.tensor([-0.8, 0.6])
        neg = torch.tensor([0.6, 0.8])
        loss = neural_net.get_triplet_loss(anchor, pos, neg)
        loss_value = loss.data.numpy().item()
        self.assertAlmostEqual(loss_value, 1 + myconfig.TRIPLET_ALPHA)

    def test_get_triplet_loss_from_batch_output1(self):
        batch_output = torch.tensor([[0.6, 0.8], [-0.8, 0.6], [0.6, 0.8]])
        loss = neural_net.get_triplet_loss_from_batch_output(
            batch_output, batch_size=1)
        loss_value = loss.data.numpy().item()
        self.assertAlmostEqual(loss_value, 1 + myconfig.TRIPLET_ALPHA)

    def test_get_triplet_loss_from_batch_output1(self):
        batch_output = torch.tensor(
            [[0.6, 0.8], [-0.8, 0.6], [0.6, 0.8],
             [0.6, 0.8], [-0.8, 0.6], [0.6, 0.8]])
        loss = neural_net.get_triplet_loss_from_batch_output(
            batch_output, batch_size=2)
        loss_value = loss.data.numpy().item()
        self.assertAlmostEqual(loss_value, 1 + myconfig.TRIPLET_ALPHA)

    def test_train_unilstm_network(self):
        myconfig.BI_LSTM = False
        losses = neural_net.train_network(num_steps=2)
        self.assertEqual(len(losses), 2)

    def test_train_bilstm_network(self):
        myconfig.BI_LSTM = True
        losses = neural_net.train_network(num_steps=2)
        self.assertEqual(len(losses), 2)


class TestEvaluation(unittest.TestCase):
    def setUp(self):
        myconfig.BI_LSTM = False
        self.encoder = neural_net.SpeakerEncoder().to(myconfig.DEVICE)

    def test_run_unilstm_inference(self):
        features = feature_extraction.extract_features(os.path.join(
            myconfig.TEST_DATA_DIR, "61/70968/61-70968-0000.flac"))
        embedding = evaluation.run_inference(features, self.encoder)
        self.assertEqual(embedding.shape, (myconfig.LSTM_HIDDEN_SIZE,))

    def test_run_bilstm_inference(self):
        myconfig.BI_LSTM = True
        self.encoder = neural_net.SpeakerEncoder().to(myconfig.DEVICE)
        features = feature_extraction.extract_features(os.path.join(
            myconfig.TEST_DATA_DIR, "61/70968/61-70968-0000.flac"))
        embedding = evaluation.run_inference(features, self.encoder)
        self.assertEqual(embedding.shape, (2 * myconfig.LSTM_HIDDEN_SIZE,))

    def test_cosine_similarity(self):
        a = np.array([0.6, 0.8, 0.0])
        b = np.array([0.6, 0.8, 0.0])
        self.assertAlmostEqual(1.0, evaluation.cosine_similarity(a, b))

        a = np.array([0.6, 0.8, 0.0])
        b = np.array([0.8, -0.6, 0.0])
        self.assertAlmostEqual(0.0, evaluation.cosine_similarity(a, b))

        a = np.array([0.6, 0.8, 0.0])
        b = np.array([0.8, 0.6, 0.0])
        self.assertAlmostEqual(0.96, evaluation.cosine_similarity(a, b))

        a = np.array([0.6, 0.8, 0.0])
        b = np.array([0.0, 0.8, -0.6])
        self.assertAlmostEqual(0.64, evaluation.cosine_similarity(a, b))

    def test_compute_scores(self):
        labels, scores = evaluation.compute_scores(self.encoder, 3)
        self.assertListEqual(labels, [1, 0, 1, 0, 1, 0])
        self.assertEqual(len(scores), 6)

    def test_compute_eer(self):
        labels = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1]
        scores = [0.2, 0.3, 0.4, 0.59, 0.6, 0.588, 0.602, 0.7, 0.8, 0.9]
        eer, eer_threshold = evaluation.compute_eer(labels, scores)
        self.assertAlmostEqual(eer, 0.2)
        self.assertAlmostEqual(eer_threshold, 0.59)


if __name__ == "__main__":
    unittest.main()

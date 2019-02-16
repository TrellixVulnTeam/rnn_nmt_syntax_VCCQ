import tarfile
import torch
from model import EOS_token, DEVICE


class WMTDataset(object):
    """
    Prepare data from WMTDataset
    """
    def __init__(self, max_length, reverse=False):
        self.word2index = {}
        self.word2count = {}
        self.index2word = {0: "SOS", 1: "EOS"}
        self.num_words = 2  # Count SOS and EOS
        self.tar_path = "/mnt/nfs/work1/miyyer/datasets/wmt/wmt_en_de.tar.gz"
        self.vocab_file = 'vocab.bpe.32000'
        self.splits = {
            'valid': 'newstest2013.tok',
            'test': 'newstest2014.tok',
            'train': 'train.tok.clean'
        }
        self.reverse = reverse
        self.max_length = max_length
        self.pairs = self.prepare_data()

    def read_vocab(self):
        t = tarfile.open(self.tar_path, "r")
        vocab = str(t.extractfile(self.vocab_file).read(), 'utf-8').strip().split('\n')
        for v in vocab:
            self.add_word(v)

    def add_word(self, word):
        if word not in self.word2index:
            self.word2index[word] = self.num_words
            self.word2count[word] = 1
            self.index2word[self.num_words] = word
            self.num_words += 1
        else:
            self.word2count[word] += 1

    def read_langs(self):
        print("Reading lines...")

        t = tarfile.open(self.tar_path, "r")

        en_lines = str(t.extractfile('%s.bpe.32000.en' % (self.splits['train'])).read(), 'utf-8').strip().split('\n')
        de_lines = str(t.extractfile('%s.bpe.32000.de' % (self.splits['train'])).read(), 'utf-8').strip().split('\n')

        # Split every line into pairs
        pairs = [[s1, s2] for s1, s2 in zip(de_lines, en_lines)]

        # Reverse pairs, make Lang instances
        if self.reverse:
            pairs = [list(reversed(p)) for p in pairs]

        return pairs

    def prepare_data(self):
        pairs = self.read_langs()
        print("Read %s sentence pairs" % len(pairs))
        pairs = self.filter_pairs(pairs)
        print("Trimmed to %s sentence pairs" % len(pairs))
        print("Counting words from vocab file...")
        self.read_vocab()
        print("Counted words:", self.num_words)
        return pairs

    def filter_pair(self, p):
        return len(p[0].split(' ')) < self.max_length and \
               len(p[1].split(' ')) < self.max_length

    def filter_pairs(self, pairs):
        return [pair for pair in pairs if self.filter_pair(pair)]

    def indexes_from_sentence(self, sentence):
        return [self.word2index[word] for word in sentence.split(' ')]

    def tensor_from_sentence(self, sentence):
        indexes = self.indexes_from_sentence(sentence)
        indexes.append(EOS_token)
        return torch.tensor(indexes, dtype=torch.long, device=DEVICE).view(-1, 1)

    def tensors_from_pair(self, pair):
        input_tensor = self.tensor_from_sentence(pair[0])
        target_tensor = self.tensor_from_sentence(pair[1])
        return input_tensor, target_tensor
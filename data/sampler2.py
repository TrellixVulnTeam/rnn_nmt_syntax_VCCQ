'''
A module implementing various data samplers for datasets.
'''
import numpy as np
import psutil
from model import NUM_DEVICES
from torch.utils.data import Sampler


class RandomBatchSampler(Sampler):
    ''' A sampler that tries to select batches that have a given total sequence length '''
    def __init__(self, datasource, batch_size, drop_last=False, shuffle=False):
        super(RandomBatchSampler, self).__init__(datasource)

        self.batches = []
        self.shuffle = shuffle

        data_indices = [i[0] for i in sorted(enumerate(datasource), key=lambda x: len(x[1]), reverse=True)]

        batch = []

        for idx in data_indices:
            batch.append(idx)
            if len(batch) == batch_size:
                self.batches.append(batch)
                batch = []

        if not drop_last and len(batch) > 0:
            self.batches.append(batch)

    def __len__(self):
        ''' Estimate the number of batches per iteration '''
        return len(self.batches)

    def __iter__(self):
        ''' Iterate over the batches '''
        batch_indices = np.arange(len(self))
        if self.shuffle:
            np.random.shuffle(batch_indices)

        for idx in batch_indices:
            yield self.batches[idx]


class SequenceLengthSampler3(Sampler):
    ''' A sampler that tries to select batches that have a given total sequence length '''
    def __init__(self, datasource, batch_size, drop_last=False, shuffle=False):
        super(SequenceLengthSampler3, self).__init__(datasource)

        self.batches = []
        self.shuffle = shuffle

        data_indices = [i[0] for i in sorted(enumerate(datasource), key=lambda x: len(x[1][1]), reverse=True)]
        print("example_lengths", datasource[data_indices[0]])
        print("example_lengths", len(datasource[data_indices[0]][1]))

        i = 0

        batch = []

        for idx in data_indices:
            if len(batch) == 0:
                seq_len = len(datasource[data_indices[i]][1])
                print("batch_size", batch_size)
                print("seq_len", seq_len)
                batch_max_len = batch_size // seq_len
                batch_max_len -= batch_max_len % NUM_DEVICES
                print("batch_max_len", batch_max_len)
            batch.append(idx)
            print("batch_max_len", batch_max_len)
            batch_max_len -= 1
            if batch_max_len == 0:
                self.batches.append(batch)
                batch = []

        if not drop_last and len(batch) > 0:
            self.batches.append(batch)
        print("num batches", len(self.batches))
        print("batch[0]", self.batches[0])

    def __len__(self):
        ''' Estimate the number of batches per iteration '''
        return len(self.batches)

    def __iter__(self):
        ''' Iterate over the batches '''
        batch_indices = np.arange(len(self))
        if self.shuffle:
            np.random.shuffle(batch_indices)

        for idx in batch_indices:
            print("idx", idx)
            yield self.batches[idx]


class SequenceLengthSampler(Sampler):
    ''' A sampler that tries to select batches that have a given total sequence length '''
    def __init__(self, example_lengths, batch_size, drop_last=False, shuffle=False):
        super(SequenceLengthSampler, self).__init__(example_lengths)

        self.batches = []
        self.shuffle = shuffle

        data_indices = [i[0] for i in sorted(enumerate(example_lengths), key=lambda x: x[1][1], reverse=True)]

        i = 0

        while i < len(data_indices):
            seq_len = example_lengths[data_indices[i]][1]
            batch_max_len = batch_size // seq_len
            batch_max_len -= batch_max_len % NUM_DEVICES
            self.batches.append(data_indices[i:i + batch_max_len])
            i += batch_max_len

        if drop_last and len(self.batches[-1]) < batch_max_len:
            self.batches = self.batches[:-1]
        # print("num batches", len(self.batches))

    def __len__(self):
        ''' Estimate the number of batches per iteration '''
        return len(self.batches)

    def __iter__(self):
        ''' Iterate over the batches '''
        batch_indices = np.arange(len(self))
        if self.shuffle:
            np.random.shuffle(batch_indices)

        for idx in batch_indices:
            yield self.batches[idx]


class SequenceLengthSampler2(Sampler):
    ''' A sampler that tries to select batches that have a given total sequence length '''
    def __init__(self, example_lengths, batch_size, drop_last=False, shuffle=False):
        super(SequenceLengthSampler2, self).__init__(example_lengths)

        self.batches = []
        self.shuffle = shuffle
        self.batch_size = batch_size
        self.example_lengths = example_lengths
        self.drop_last = drop_last
        self.indices = [i[0] for i in sorted(enumerate(example_lengths), key=lambda x: x[1][1], reverse=True)]



    def __len__(self):
        ''' Estimate the number of batches per iteration '''
        return len(self.batches)

    def __iter__(self):
        ''' Iterate over the batches '''
        vm = psutil.virtual_memory()
        print("1virtual_memory", vm)
        max_tokens = self.batch_size
        max_sentences = float("Inf")
        bsz_mult = NUM_DEVICES

        batch = []

        def is_batch_full(num_tokens):
            if len(batch) == 0:
                return False
            if len(batch) == max_sentences:
                return True
            if num_tokens > max_tokens:
                return True
            return False

        sample_len = 0
        sample_lens = []
        for idx in self.indices:
            sample_lens.append(self.example_lengths[idx][1])
            sample_len = max(sample_len, sample_lens[-1])
            assert sample_len <= max_tokens, "sentence at index {idx} exceeds max_tokens limit!".format(idx=idx)
            num_tokens = (len(batch) + 1) * sample_len
            if is_batch_full(num_tokens):
                mod_len = max(
                    bsz_mult * (len(batch) // bsz_mult),
                    len(batch) % bsz_mult,
                )
                vm = psutil.virtual_memory()
                print("2virtual_memory", vm)
                yield batch[:mod_len]
                batch = batch[mod_len:]
                sample_lens = sample_lens[mod_len:]
                sample_len = max(sample_lens) if len(sample_lens) > 0 else 0

            batch.append(idx)

        if len(batch) > 0 and not self.drop_last:
            yield batch
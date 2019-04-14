import collections

class Box(collections.namedtuple(
    'Box', (
        'name', 'length', 'width', 'height', 'length_dimension',
        'weight', 'weight_dimension',
    )))

    @property
    def volume(self):
        return self.length * self.width * self.height


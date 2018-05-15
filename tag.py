class Foo(object):

    def __init__(self):
        self.name = 'alex'


# 不允许使用 obj.name
obj = Foo()

print(obj.name)
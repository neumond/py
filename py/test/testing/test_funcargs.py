import py

class TestFuncargs:
    def test_funcarg_lookupfails(self, testdir):
        testdir.makeconftest("""
            class ConftestPlugin:
                def pytest_funcarg__xyzsomething(self, request):
                    return 42
        """)
        item = testdir.getitem("def test_func(some): pass")
        exc = py.test.raises(LookupError, "item._setupfuncargs()")
        s = str(exc.value)
        assert s.find("xyzsomething") != -1

    def test_funcarg_lookup_default(self, testdir):
        item = testdir.getitem("def test_func(some, other=42): pass")
        class Provider:
            def pytest_funcarg__some(self, request):
                return request.function.__name__
        item.config.pluginmanager.register(Provider())
        item._setupfuncargs()
        assert len(item.funcargs) == 1

    def test_funcarg_lookup_default_gets_overriden(self, testdir):
        item = testdir.getitem("def test_func(some=42, other=13): pass")
        class Provider:
            def pytest_funcarg__other(self, request):
                return request.function.__name__
        item.config.pluginmanager.register(Provider())
        item._setupfuncargs()
        assert len(item.funcargs) == 1
        name, value = item.funcargs.popitem()
        assert name == "other"
        assert value == item.name 

    def test_funcarg_basic(self, testdir):
        item = testdir.getitem("def test_func(some, other): pass")
        class Provider:
            def pytest_funcarg__some(self, request):
                return request.function.__name__ 
            def pytest_funcarg__other(self, request):
                return 42
        item.config.pluginmanager.register(Provider())
        item._setupfuncargs()
        assert len(item.funcargs) == 2
        assert item.funcargs['some'] == "test_func"
        assert item.funcargs['other'] == 42

    def test_funcarg_lookup_modulelevel(self, testdir):
        modcol = testdir.getmodulecol("""
            def pytest_funcarg__something(request):
                return request.function.__name__

            class TestClass:
                def test_method(self, something):
                    pass 
            def test_func(something):
                pass 
        """)
        item1, item2 = testdir.genitems([modcol])
        item1._setupfuncargs()
        assert item1.funcargs['something'] ==  "test_method"
        item2._setupfuncargs()
        assert item2.funcargs['something'] ==  "test_func"

class TestRequest:
    def test_request_attributes(self, testdir):
        item = testdir.getitem("""
            def pytest_funcarg__something(request): pass
            def test_func(something): pass
        """)
        req = item.getrequest("other")
        assert req.argname == "other"
        assert req.function == item.obj 
        assert req.function.__name__ == "test_func" 
        assert req.config == item.config 
        assert repr(req).find(req.function.__name__) != -1
        
    def test_request_contains_funcargs_methods(self, testdir):
        modcol = testdir.getmodulecol("""
            def pytest_funcarg__something(request):
                pass
            class TestClass:
                def pytest_funcarg__something(self, request):
                    pass
                def test_method(self, something):
                    pass 
        """)
        item1, = testdir.genitems([modcol])
        assert item1.name == "test_method"
        methods = item1.getrequest("something")._methods 
        assert len(methods) == 2
        method1, method2 = methods 
        assert not hasattr(method1, 'im_self')
        assert method2.im_self is not None

    def test_request_call_next_provider(self, testdir):
        item = testdir.getitem("""
            def pytest_funcarg__something(request): pass
            def test_func(something): pass
        """)
        req = item.getrequest("something")
        val = req.call_next_provider()
        assert val is None
        py.test.raises(req.Error, "req.call_next_provider()")

    def test_request_addfinalizer(self, testdir):
        item = testdir.getitem("""
            def pytest_funcarg__something(request): pass
            def test_func(something): pass
        """)
        req = item.getrequest("something")
        l = [1]
        req.addfinalizer(l.pop)
        item.teardown()

    def test_request_maketemp(self, testdir):
        item = testdir.getitem("def test_func(): pass")
        req = item.getrequest("xxx")
        tmpdir = req.maketempdir()
        tmpdir2 = req.maketempdir()
        assert tmpdir != tmpdir2
        assert tmpdir.basename.startswith("test_func")
        assert tmpdir2.basename.startswith("test_func")

    def test_request_getmodulepath(self, testdir):
        modcol = testdir.getmodulecol("def test_somefunc(): pass")
        item, = testdir.genitems([modcol])
        req = item.getrequest("hello")
        assert req.fspath == modcol.fspath 
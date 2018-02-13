import pytest
from bw_presamples import ParameterPresamples

try:
    from bw2data import mapping, Database
    from bw2data.tests import bw2test
    from bw2data.parameters import (
        ActivityParameter,
        DatabaseParameter,
        Group,
        ProjectParameter,
        parameters,
    )
    from bw_presamples.models import ParameterizedBrightwayModel
except ImportError:
    bw2test = pytest.mark.skip


@bw2test
def test_chain_loading():
    Database("B").register()
    Database("K").register()
    Group.create(name="G", order=["A"])
    ActivityParameter.create(
        group="A",
        database="B",
        code="C",
        name="D",
        formula="2 ** 3",
        amount=1,

    )
    ActivityParameter.create(
        group="A",
        database="B",
        code="E",
        name="F",
        formula="foo + bar + D",
        amount=2,
    )
    ActivityParameter.create(
        group="G",
        database="K",
        code="H",
        name="J",
        formula="F + D * 2",
        amount=3,
    )
    DatabaseParameter.create(
        database="B",
        name="foo",
        formula="2 ** 2",
        amount=5,
    )
    ProjectParameter.create(
        name="bar",
        formula="2 * 2 * 2",
        amount=6,
    )
    parameters.recalculate()
    m = ParameterizedBrightwayModel("A")
    m.load_parameter_data()
    expected = {
        'A__D': {
            'database': 'B',
            'code': 'C',
            'formula': '(2 ** 3)',
            'amount': 8.0,
            'original': 'D'
        },
        'A__F': {
            'database': 'B',
            'code': 'E',
            'formula': '((B__foo + project__bar) + A__D)',
            'amount': 20.0,
            'original': 'F'
        },
        'B__foo': {
            'database': 'B',
            'formula': '(2 ** 2)',
            'amount': 4.0,
            'original': 'foo'
        },
        'project__bar': {
            'formula': '((2 * 2) * 2)',
            'amount': 8.0,
            'original': 'bar'
        }
    }
    assert m.data == expected

@bw2test
def test_chain_loading_complicated():
    Database("db").register()
    Group.create(name="D", order=[])
    Group.create(name="E", order=[])
    Group.create(name="B", order=["E"])
    Group.create(name="C", order=["D", "E"])
    Group.create(name="A", order=["C", "B"])
    ProjectParameter.create(
        name="p1",
        amount=1,
    )
    ProjectParameter.create(
        name="p2",
        amount=1,
    )
    DatabaseParameter.create(
        database="db",
        name="db1",
        formula="2 * p1",
        amount=2,
    )
    DatabaseParameter.create(
        database="db",
        name="db2",
        amount=2,
    )
    ActivityParameter.create(
        group="D",
        database="db",
        code="D1",
        name="d1",
        formula="p1 + db1",
        amount=3,
    )
    ActivityParameter.create(
        group="E",
        database="db",
        code="E1",
        name="e1",
        formula="p1 + p2 + db2",
        amount=4,
    )
    ActivityParameter.create(
        group="C",
        database="db",
        code="C1",
        name="c1",
        formula="(e1 - d1) * 5",
        amount=5,
    )
    ActivityParameter.create(
        group="B",
        database="db",
        code="B1",
        name="b1",
        formula="e1 * 2 - 2",
        amount=6,
    )
    ActivityParameter.create(
        group="A",
        database="db",
        code="A1",
        name="a1",
        formula="b1 + c1 - db1 - 2",
        amount=7,
    )
    parameters.recalculate()
    pbm = ParameterizedBrightwayModel("A")
    pbm.load_parameter_data()
    expected = {
        'A__a1': {
            'amount': 7.0,
           'code': 'A1',
           'database': 'db',
           'formula': '(((B__b1 + C__c1) - db__db1) - 2)',
           'original': 'a1'},
        'B__b1': {
            'amount': 6.0,
           'code': 'B1',
           'database': 'db',
           'formula': '((E__e1 * 2) - 2)',
           'original': 'b1'},
        'C__c1': {
            'amount': 5.0,
           'code': 'C1',
           'database': 'db',
           'formula': '((E__e1 - D__d1) * 5)',
           'original': 'c1'},
        'D__d1': {
            'amount': 3.0,
           'code': 'D1',
           'database': 'db',
           'formula': '(project__p1 + db__db1)',
           'original': 'd1'},
        'E__e1': {
            'amount': 4.0,
            'code': 'E1',
            'database': 'db',
            'formula': '((project__p1 + project__p2) + db__db2)',
            'original': 'e1'},
        'db__db1': {
            'amount': 2.0,
            'database': 'db',
            'formula': '(2 * project__p1)',
            'original': 'db1'},
        'db__db2': {
            'amount': 2.0,
            'database': 'db',
            'original': 'db2'},
        'project__p1': {
            'amount': 1.0,
            'original': 'p1'},
        'project__p2': {
            'amount': 1.0,
            'original': 'p2'}
    }
    assert pbm.data == expected

@bw2test
def test_load_existing_complete():
    # Use same structure as in complicated example, but pre-create some presamples packages
    # Start with `project`
    ProjectParameter.create(
        name="p1",
        amount=1,
    )
    ProjectParameter.create(
        name="p2",
        amount=1,
    )
    parameters.recalculate()
    pbm = ParameterizedBrightwayModel("project")
    pbm.load_parameter_data()
    result = pbm.calculate_static()
    expected = {'project__p1': 1, 'project__p2': 1}
    assert result == expected
    for obj in pbm.data.values():
        obj['amount'] = 10
    _, dirpath_project = pbm.save_presample('project-test')
    pp = ParameterPresamples(dirpath_project)
    assert len(pp) == 1
    assert pp['project-test'] == {'project__p1': 10, 'project__p2': 10}

    # We will also do group 'D'; this will include database parameters, which will we purge ourselves
    Database("db").register()
    Group.create(name="D", order=[])
    DatabaseParameter.create(
        database="db",
        name="db1",
        formula="2 * p1",
        amount=2,
    )
    DatabaseParameter.create(
        database="db",
        name="db2",
        amount=2,
    )
    ActivityParameter.create(
        group="D",
        database="db",
        code="D1",
        name="d1",
        formula="p1 + db1",
        amount=3,
    )
    parameters.recalculate()
    pbm = ParameterizedBrightwayModel("D")
    pbm.load_existing(dirpath_project)
    expected = {'project-test': {'project__p1': 10, 'project__p2': 10}}
    assert pbm.global_params == expected

    pbm.load_parameter_data()
    expected = {
        'D__d1': {
            'database': 'db',
            'code': 'D1',
            'formula': '(project__p1 + db__db1)',
            'amount': 3.0,
            'original': 'd1'},
        'db__db1': {
            'database': 'db',
            'formula': '(2 * project__p1)',
            'amount': 2.0,
            'original': 'db1'},
        'db__db2': {
            'database': 'db',
            'amount': 2.0,
            'original': 'db2'},
    }
    assert pbm.data == expected

    # Want to calculate database parameters dynamically
    pbm.data = {'D__d1': pbm.data['D__d1']}
    pbm.data['D__d1']['amount'] = 12
    _, dirpath_d = pbm.save_presample('D-test')
    pp = ParameterPresamples(dirpath_d)
    assert len(pp) == 1
    assert pp['D-test'] == {'D__d1': 12}

    # Create rest of parameters
    Group.create(name="E", order=[])
    Group.create(name="B", order=["E"])
    Group.create(name="C", order=["D", "E"])
    Group.create(name="A", order=["C", "B"])
    ActivityParameter.create(
        group="E",
        database="db",
        code="E1",
        name="e1",
        formula="p1 + p2 + db2",
        amount=4,
    )
    ActivityParameter.create(
        group="C",
        database="db",
        code="C1",
        name="c1",
        formula="(e1 - d1) * 5",
        amount=5,
    )
    ActivityParameter.create(
        group="B",
        database="db",
        code="B1",
        name="b1",
        formula="e1 * 2 - 2",
        amount=6,
    )
    ActivityParameter.create(
        group="A",
        database="db",
        code="A1",
        name="a1",
        formula="b1 + c1 - db1 - 2",
        amount=7,
    )
    parameters.recalculate()
    pbm = ParameterizedBrightwayModel("A")
    pbm.load_existing(dirpath_project)
    pbm.load_existing(dirpath_d)
    pbm.load_parameter_data()
    expected = {
        'A__a1': {
            'amount': 7.0,
           'code': 'A1',
           'database': 'db',
           'formula': '(((B__b1 + C__c1) - db__db1) - 2)',
           'original': 'a1'},
        'B__b1': {
            'amount': 6.0,
           'code': 'B1',
           'database': 'db',
           'formula': '((E__e1 * 2) - 2)',
           'original': 'b1'},
        'C__c1': {
            'amount': 5.0,
           'code': 'C1',
           'database': 'db',
           'formula': '((E__e1 - D__d1) * 5)',
           'original': 'c1'},
        'E__e1': {
            'amount': 4.0,
            'code': 'E1',
            'database': 'db',
            'formula': '((project__p1 + project__p2) + db__db2)',
            'original': 'e1'},
        'db__db1': {
            'amount': 2.0,
            'database': 'db',
            'formula': '(2 * project__p1)',
            'original': 'db1'},
        'db__db2': {
            'amount': 2.0,
            'database': 'db',
            'original': 'db2'},
    }
    assert pbm.data == expected
    print(pbm.global_params)
    print(pbm._flatten_global_params(pbm.global_params))
    result = pbm.calculate_static()

    expected = {
        'A__a1': 70.0,
        'B__b1': 42.0,
        'C__c1': 50.0,
        'E__e1': 22.0,
        'db__db1': 20.0,
        'db__db2': 2.0
    }
    assert result == expected

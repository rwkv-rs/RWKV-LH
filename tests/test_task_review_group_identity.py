from copy import deepcopy
import pytest
from test_task_review import bundle, assess, rebind
from rwkv_lh import task_review as review


def grid(bundle, changed_field='source', drift=False):
    rows=[]
    for task in ('health','another-file'):
        for repeat in (1,2):
            b=deepcopy(bundle)
            b[0]['task_id']=task
            b[1].update(task_id=task, repeat=repeat, run_id=f'{task}-{repeat}')
            b[0]['execution_identity'][changed_field]=review.digest(f'{task}-{changed_field}')
            if drift and task=='health' and repeat==2:
                b[0]['execution_identity'][changed_field]=review.digest('changed during repeats')
            b[1]['execution_identity']=deepcopy(b[0]['execution_identity'])
            rebind(b);rows.append(assess(b))
    return rows


@pytest.mark.parametrize('field',['source','budget'])
def test_distinct_tasks_can_have_distinct_frozen_inputs_and_budgets(bundle,field):
    result=review.quality_gate(grid(bundle,field),task_ids=['health','another-file'],repeats=2,arm='zero')
    assert result['complete_grid']
    assert result['consistent_identity_and_contract']
    assert result['passed']


def test_each_task_must_keep_its_identity_across_repeats(bundle):
    result=review.quality_gate(grid(bundle,drift=True),task_ids=['health','another-file'],repeats=2,arm='zero')
    assert result['complete_grid']
    assert not result['consistent_identity_and_contract']
    assert not result['passed']

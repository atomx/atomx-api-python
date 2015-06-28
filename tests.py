import pytest


@pytest.fixture(scope="session")
def atomx():
    from atomx import Atomx
    return Atomx('daniel@atomx.com', 'password', 'http://127.0.0.1:6543/v1/')


def test_limit(atomx):
    creatives = atomx.get('creatives', limit=5)
    assert len(creatives) == 5

def test_update(atomx):
    NEW_TITLE = 'test title'
    creative = atomx.get('creatives', id=5)
    creative.title = NEW_TITLE
    creative.update()
    creative = atomx.get('creatives', id=5)
    assert creative.title == NEW_TITLE


def test_create(atomx):
    from atomx.models import Profile
    profile = Profile(advertiser_id=23, name='test profile')
    profile.create(atomx)
    profile_new = atomx.get('profile', id=profile.id)
    assert profile.name == profile_new.name

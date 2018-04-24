import pytest
from django.urls import reverse

from pretalx.event.models import TeamInvite


@pytest.mark.django_db
def test_orga_successful_login(client, user, template_patch):
    user.set_password('testtest')
    user.save()
    response = client.post(reverse('orga:login'), data={'username': user.nick, 'password': 'testtest'}, follow=True)
    assert response.status_code == 200


@pytest.mark.django_db
def test_orga_redirect_login(client, orga_user, event):
    queryparams = 'foo=bar&something=else'
    request_url = event.orga_urls.base + '/?' + queryparams
    response = client.get(request_url, follow=True)
    assert response.status_code == 200
    assert response.redirect_chain[-1] == (f'/orga/login/?next={event.orga_urls.base}/&{queryparams}', 302)

    response = client.post(response.redirect_chain[-1][0], data={'username': orga_user.nick, 'password': 'orgapassw0rd'}, follow=True)
    assert response.status_code == 200
    assert event.name in response.content.decode()
    assert response.redirect_chain[-1][0] == request_url


@pytest.mark.django_db
def test_orga_accept_invitation_once(client, event, invitation):
    team = invitation.team
    count = invitation.team.members.count()
    token = invitation.token
    response = client.post(
        reverse('orga:invitation.view', kwargs={'code': invitation.token}),
        {
            'register_username': 'newuser',
            'register_email': invitation.email,
            'register_password': 'f00baar!',
            'register_password_repeat': 'f00baar!',
        },
        follow=True,
    )
    assert response.status_code == 200
    assert team.members.count() == count + 1
    assert team.invites.count() == 0
    with pytest.raises(TeamInvite.DoesNotExist):
        invitation.refresh_from_db()
    response = client.get(
        reverse('orga:invitation.view', kwargs={'code': token}),
        follow=True
    )
    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize('duplicate', ['username', 'email'])
def test_orga_registration_errors(client, event, invitation, user, duplicate):
    team = invitation.team
    count = invitation.team.members.count()
    response = client.post(
        reverse('orga:invitation.view', kwargs={'code': invitation.token}),
        {
            'register_username': user.nick if duplicate == 'username' else 'newuser',
            'register_email': user.email if duplicate == 'email' else invitation.email,
            'register_password': 'f00baar!',
            'register_password_repeat': 'f00baar!',
        },
        follow=True,
    )
    assert response.status_code == 200
    assert team.members.count() == count
    assert team.invites.count() == 1


@pytest.mark.django_db
def test_orga_incorrect_invite_token(client, event, invitation):
    response = client.get(
        reverse('orga:invitation.view', kwargs={'code': invitation.token + 'WRONG'}),
        follow=True
    )
    assert response.status_code == 404

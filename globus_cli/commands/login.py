import click

from globus_sdk import AuthClient, AccessTokenAuthorizer

from globus_cli.safeio import safeprint
from globus_cli.parsing import common_options
from globus_cli.config import (
    AUTH_RT_OPTNAME, TRANSFER_RT_OPTNAME,
    AUTH_AT_OPTNAME, TRANSFER_AT_OPTNAME,
    AUTH_AT_EXPIRES_OPTNAME, TRANSFER_AT_EXPIRES_OPTNAME,
    WHOAMI_ID_OPTNAME, WHOAMI_USERNAME_OPTNAME,
    WHOAMI_EMAIL_OPTNAME, WHOAMI_NAME_OPTNAME,
    internal_auth_client, write_option, lookup_option)


_SHARED_EPILOG = ("""\


You can always check your current identity with
  globus whoami

Logout of the Globus CLI with
  globus logout
""")

_LOGIN_EPILOG = ("""\

You have successfully logged in to the Globus CLI as {}
""") + _SHARED_EPILOG

_LOGGED_IN_RESPONSE = ("""\
You are already logged in!

You may force a new login with
  globus login --force
""") + _SHARED_EPILOG


@click.command('login',
               short_help=('Login to Globus to get credentials for '
                           'the Globus CLI'),
               help=('Get credentials for the Globus CLI. '
                     'Necessary before any Globus CLI commands which require '
                     'authentication will work'))
@common_options(no_format_option=True, no_map_http_status_option=True)
@click.option('--force', is_flag=True,
              help=('Do a fresh login, ignoring any existing credentials'))
def login_command(force):
    if not force and check_logged_in():
        safeprint(_LOGGED_IN_RESPONSE)

    if force or not check_logged_in():
        do_login_flow()


def check_logged_in():
    # first, pull up all of the data from config and see what we can get
    # we can skip the access tokens and their expiration times as those are not
    # strictly necessary
    transfer_rt = lookup_option(TRANSFER_RT_OPTNAME)
    auth_rt = lookup_option(AUTH_RT_OPTNAME)
    # whoami data -- consider required for now
    whoami_id = lookup_option(WHOAMI_ID_OPTNAME)
    whoami_username = lookup_option(WHOAMI_USERNAME_OPTNAME)
    whoami_email = lookup_option(WHOAMI_EMAIL_OPTNAME)
    whoami_name = lookup_option(WHOAMI_NAME_OPTNAME)

    # if any of these values are null return False
    if (transfer_rt is None or auth_rt is None or
            whoami_id is None or whoami_username is None or
            whoami_email is None or whoami_name is None):
        return False

    # TODO: check that the tokens are valid
    return True


def do_login_flow():
    # build the NativeApp client object
    native_client = internal_auth_client()

    # and do the Native App Grant flow
    native_client.oauth2_start_flow_native_app(refresh_tokens=True)

    # prompt
    linkprompt = 'Please login to Globus here'
    safeprint('{0}:\n{1}\n{2}\n{1}\n'
              .format(linkprompt, '-' * len(linkprompt),
                      native_client.oauth2_get_authorize_url()))

    # come back with auth code
    auth_code = click.prompt(
        'Enter the resulting Authorization Code here').strip()

    # exchange, done!
    tkn = native_client.oauth2_exchange_code_for_tokens(auth_code)
    tkn = tkn.by_resource_server

    # extract access tokens from final response
    transfer_at = (
        tkn['transfer.api.globus.org']['access_token'])
    transfer_at_expires = (
        tkn['transfer.api.globus.org']['expires_at_seconds'])
    transfer_rt = (
        tkn['transfer.api.globus.org']['refresh_token'])
    auth_at = (
        tkn['auth.globus.org']['access_token'])
    auth_at_expires = (
        tkn['auth.globus.org']['expires_at_seconds'])
    auth_rt = (
        tkn['auth.globus.org']['refresh_token'])

    # get the identity that the tokens were issued to
    auth_client = AuthClient(authorizer=AccessTokenAuthorizer(auth_at))
    res = auth_client.get('/p/whoami')

    # get the primary identity
    # note: Auth's /p/whoami response does not mark an identity as
    # "primary" but by way of its implementation, the first identity
    # in the list is the primary.
    identity = res['identities'][0]

    # write data to config
    # TODO: remove once we deprecate these fully
    write_option('transfer_token', transfer_at, section='general')
    write_option('auth_token', auth_at, section='general')
    # new values we want to use moving forward
    write_option(TRANSFER_RT_OPTNAME, transfer_rt)
    write_option(TRANSFER_AT_OPTNAME, transfer_at)
    write_option(TRANSFER_AT_EXPIRES_OPTNAME, transfer_at_expires)
    write_option(AUTH_RT_OPTNAME, auth_rt)
    write_option(AUTH_AT_OPTNAME, auth_at)
    write_option(AUTH_AT_EXPIRES_OPTNAME, auth_at_expires)
    # whoami data
    write_option(WHOAMI_ID_OPTNAME, identity['id'])
    write_option(WHOAMI_USERNAME_OPTNAME, identity['username'])
    write_option(WHOAMI_EMAIL_OPTNAME, identity['email'])
    write_option(WHOAMI_NAME_OPTNAME, identity['name'])

    safeprint(_LOGIN_EPILOG.format(identity['username']))
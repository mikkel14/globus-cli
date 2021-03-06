import click

from globus_cli.parsing import common_options, ENDPOINT_PLUS_REQPATH
from globus_cli.safeio import formatted_print, FORMAT_TEXT_RAW

from globus_cli.services.transfer import get_client, autoactivate


@click.command('rename', help='Rename a file or directory on an endpoint')
@common_options
@click.argument('source', metavar='ENDPOINT_ID:SOURCE_PATH',
                type=ENDPOINT_PLUS_REQPATH)
@click.argument('destination', metavar='ENDPOINT_ID:DEST_PATH',
                type=ENDPOINT_PLUS_REQPATH)
def rename_command(source, destination):
    """
    Executor for `globus rename`
    """
    source_ep, source_path = source
    dest_ep, dest_path = destination

    if source_ep != dest_ep:
        raise click.UsageError(('rename requires that the source and dest '
                                'endpoints are the same, {} != {}')
                               .format(source_ep, dest_ep))
    endpoint_id = source_ep

    client = get_client()
    autoactivate(client, endpoint_id, if_expires_in=60)

    res = client.operation_rename(endpoint_id, oldpath=source_path,
                                  newpath=dest_path)
    formatted_print(res, text_format=FORMAT_TEXT_RAW, response_key='message')

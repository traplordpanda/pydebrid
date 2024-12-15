from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TaskID,
    DownloadColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
    TransferSpeedColumn,
)
from rich.table import Table
from rich.console import Console

from pydebrid.models import TorrentInfo, TorrentData


class JobTracker:
    """
    The JobTracker class is responsible for tracking the progress of jobs for rich output.

    Attributes:
        job_id (str): The unique identifier for the job.
        progress (int): The current progress of the job, represented as a percentage.
        status (str): The current status of the job. Possible values are 'Not Started', 'In Progress', 'Completed', and 'Failed'.
        start_time (datetime): The time when the job was started.
        end_time (datetime): The time when the job was completed.

    Methods:
        start_job(): Starts the job and sets the start_time to the current time.
        update_progress(progress: int): Updates the progress of the job.
        complete_job(): Marks the job as completed and sets the end_time to the current time.
        fail_job(): Marks the job as failed and sets the end_time to the current time.
    """

    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            BarColumn(),
            TextColumn("[progress.description]{task.fields[filename]}"),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        )
        self.table = Table.grid()
        self.live = Live(self.progress, console=Console(), refresh_per_second=4)
        self.setup_table()

    def setup_table(self):
        self.table.add_column("ID", justify="right", style="cyan", no_wrap=True)
        self.table.add_column("Progress", justify="right", style="magenta")
        self.table.add_column("Status", style="green")

    def add_task(self, description: str, total: int) -> TaskID:
        task_id = self.progress.add_task(
            description=description,
            total=total,
            status="Downloading",
            filename=description,
        )

        self.table.add_row(
            Panel.fit(
                self.progress,
                title="Download Progress",
                border_style="green",
                padding=(1, 2),
            )
        )
        return task_id

    def update_task(self, task_id: TaskID, progress_amount: float):
        self.progress.advance(task_id, progress_amount)

    def start_live_display(self):
        self.live.start()

    def stop_live_display(self):
        self.live.stop()


def torrent_table(t_data: list[TorrentInfo] | list[TorrentData]):
    table = Table(title="Torrent Details", header_style="bold magenta")

    table.add_column("Torrent Info", style="cyan")
    table.add_column("Value", style="dim")

    for torrent in t_data:
        table.add_row("Filename", torrent.filename)
        file_size_gb = torrent.bytes / 1024 / 1024 / 1024
        file_size = f'{file_size_gb:.2f} GB'
        table.add_row("Bytes", file_size)
        table.add_row("Progress", str(torrent.progress))
        table.add_row("Status", torrent.status)
        table.add_section()
    return table


def detailed_torrent_table(t_data: list[TorrentInfo]):
    table = Table(title="Torrent Details", header_style="bold magenta")

    table.add_column("Torrent Info", style="cyan")
    table.add_column("Value", style="dim")

    for torrent in t_data:
        table.add_row("Filename", torrent.filename)
        table.add_row("Status", torrent.status)
        for info in torrent.files:
            table.add_row("Path", info.path)
            table.add_row("Selected", str(info.selected))
            table.add_row()
        table.add_section()
    return table

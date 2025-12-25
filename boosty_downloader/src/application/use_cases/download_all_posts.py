"""Implements the use case for downloading all posts from a Boosty author, applying filters and caching as needed."""

import asyncio
from pathlib import Path

from boosty_downloader.src.application.di.download_context import DownloadContext
from boosty_downloader.src.application.exceptions.application_errors import (
    ApplicationCancelledError,
    ApplicationFailedDownloadError,
)
from boosty_downloader.src.application.use_cases.download_single_post import (
    DownloadSinglePostUseCase,
)
from boosty_downloader.src.infrastructure.boosty_api.core.client import BoostyAPIClient
from boosty_downloader.src.infrastructure.path_sanitizer import (
    sanitize_string,
)

#Long dirname fix START
import sys

def utf8_char_len(c):
    codepoint = ord(c)
    if codepoint <= 0x7f:
        return 1
    if codepoint <= 0x7ff:
        return 2
    if codepoint <= 0xffff:
        return 3
    if codepoint <= 0x10ffff:
        return 4
    raise ValueError('Invalid Unicode character: ' + hex(codepoint))

def utf8len(s):
    return sum(utf8_char_len(c) for c in s)

#Long dirname fix END


class DownloadAllPostUseCase:
    """
    Use case for downloading all user's posts.

    This class encapsulates the logic required to download all posts from a source.
    Initialize the use case and call its methods to perform the download operation.

    All the downloaded content parts will be saved under the specified destination path.
    """

    def __init__(
        self,
        author_name: str,
        boosty_api: BoostyAPIClient,
        destination: Path,
        download_context: DownloadContext,
    ) -> None:
        self.author_name = author_name

        self.boosty_api = boosty_api
        self.destination = destination
        self.context = download_context

    async def execute(self) -> None:
        posts_iterator = self.boosty_api.iterate_over_posts(
            author_name=self.author_name
        )

        current_page = 0

        async for page in posts_iterator:
            count = len(page.posts)
            current_page += 1

            page_task_id = self.context.progress_reporter.create_task(
                f'Got new posts: [{count}]',
                total=count,
                indent_level=0,  # Each page prints without indentation
            )

            for post_dto in page.posts:
                if not post_dto.has_access:
                    self.context.progress_reporter.warn(
                        f'Skip post ([red]no access to content[/red]): {post_dto.title}'
                    )
                    continue

                # For empty titles use post ID as a fallback (first 8 chars)
                if len(post_dto.title) == 0:
                    post_dto.title = f'Not title (id_{post_dto.id[:8]})'

                post_dto.title = (
                    sanitize_string(post_dto.title).replace('.', '').strip()
                )
                
                #Long dirname fix START
                #'5bd54c48-f79e-4e09-aa09-47f8ba83afec':
                human_filename = post_dto.title
                char_count = utf8len(human_filename);
                #2025-11-13 - НОВИНКА!! Русификатор Decktamer [128] Карточная стратегия, симулятор рогалик-головоломка (c1900ad3)
                #255-(13+11) = 231
                if char_count > 231 :
                    short_txt = '';
                    for c in human_filename :
                        c_utf8len = utf8len(short_txt + c)
                        if c_utf8len <= 231 :
                            short_txt = short_txt + c;
                    human_filename = short_txt
                #Long dirname fix END


                # date - TITLE (UUID_PART) for deduplication in case of same names with different posts
                full_post_title = f'{post_dto.created_at.date()} - {human_filename} ({post_dto.id[:8]})'
                        
                single_post_use_case = DownloadSinglePostUseCase(
                    destination=self.destination / full_post_title,
                    post_dto=post_dto,
                    download_context=self.context,
                )

                self.context.progress_reporter.update_task(
                    page_task_id,
                    advance=1,
                    description=f'Processing page [bold]{current_page}[/bold]',
                )

                max_attempts = 5
                delay = 1.0
                for attempt in range(1, max_attempts + 1):
                    try:
                        await single_post_use_case.execute()
                        break
                    except ApplicationCancelledError:
                        raise
                    except ApplicationFailedDownloadError as e:
                        if attempt == max_attempts:
                            self.context.progress_reporter.error(
                                f'Skip post after {attempt} failed attempts: {full_post_title} ({e.message})'
                            )
                        else:
                            self.context.progress_reporter.warn(
                                f'Attempt {attempt} failed for post: {full_post_title} ({e.message}), RESOURCE: ({e.resource})'
                            )
                            self.context.progress_reporter.warn(
                                f'Retrying in {delay:.1f}s... ({e.message})'
                            )
                            await asyncio.sleep(delay)
                            delay = min(delay * 1.5, 10.0)

            self.context.progress_reporter.complete_task(page_task_id)
            self.context.progress_reporter.success(
                f'--- Finished page {current_page} ---'
            )

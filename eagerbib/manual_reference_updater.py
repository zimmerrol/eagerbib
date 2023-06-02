import asyncio
import dataclasses
import inspect
from typing import (Any, AsyncGenerator, Callable, Coroutine, Generator,
                    Optional, Union)

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Center, Middle, ScrollableContainer
from textual.css.query import NoMatches
from textual.reactive import Reactive, reactive
from textual.widget import Widget
from textual.widgets import (Button, Footer, Label, LoadingIndicator,
                             Placeholder, ProgressBar, Static)

import eagerbib.output_processor as op
import eagerbib.utils as ut


@dataclasses.dataclass
class Reference:
    year: int
    title: str
    author: str
    bibliography_values: dict[str, str]


@dataclasses.dataclass
class ReferenceChoice:
    current_reference: Reference
    chosen_reference: Reference


class ReferenceChoiceTask:
    def __init__(
        self, current_reference: Reference, available_references: list[Reference]
    ) -> None:
        if current_reference in available_references:
            available_references.remove(current_reference)
        available_references.insert(0, current_reference)
        self.current_reference = current_reference
        self.available_references = available_references


class YearTitleDisplay(Static):
    year: Reactive[int] = reactive(0)
    title: Reactive[str] = reactive("")
    __composed = False

    def __init__(self, year: int, title: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.year = year
        self.title = title

    def _validate_year(self) -> str:
        value = str(self.year)

        if value == "0":
            value = ""
        return value

    def watch_year(self) -> None:
        if not self.__composed:
            return
        self.query_one("#year", expect_type=Label).update(self._validate_year())

    def watch_title(self) -> None:
        if not self.__composed:
            return
        self.query_one("#title", expect_type=Label).update(self.title)

    def compose(self) -> ComposeResult:
        yield Label(self._validate_year(), id="year")
        yield Label(self.title, id="title")
        self.__composed = True


async def await_me_maybe(callback, *args, **kwargs):
    result = callback(*args, **kwargs)
    if inspect.isawaitable(result):
        return await result
    return result


async def anext_maybe(generator: Union[Generator, AsyncGenerator]) -> Optional[Any]:
    if hasattr(generator, "__anext__"):
        return await generator.__anext__()
    else:
        return next(generator)


class ReferenceDisplay(Static):
    reference: Reactive[Optional[Reference]] = reactive(None)
    __composed = False
    can_focus = False
    can_focus_children = True

    def __init__(
        self,
        reference: Optional[Reference],
        clickable: bool = True,
        click_callback: Optional[
            Callable[[Reference], Union[None, Coroutine[Any, Any, None]]]
        ] = None,
        show_full_reference: bool = False,
        show_author: bool = True,
        show_yeartitle: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.reference = reference
        self.clickable = clickable
        self.click_callback = click_callback
        self.show_full_reference = show_full_reference
        self.show_author = show_author
        self.show_yeartitle = show_yeartitle

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.click_callback is not None:
            await await_me_maybe(self.click_callback, self.reference)

    def __get_reference_type(self):
        """Return a normalized string describing the type of the reference."""

        def normalize(s: str, n_limit: int = 55) -> str:
            """Normalize a reference_type string to be displayed in the UI."""
            s = ut.cleanup_title(s)

            if len(s) > n_limit:
                s = s[: n_limit - 3] + "..."
            return s

        recognized_reference_type_fns = {
            "inproceedings": lambda: "Proceedings ({0})".format(
                normalize(self.reference.bibliography_values.get("booktitle", ""))
            ),
            "article": lambda: "Journal article ({0})".format(
                self.reference.bibliography_values.get(
                    "journal",
                    self.reference.bibliography_values.get(
                        "publisher", self.reference.bibliography_values.get("doi", "")
                    ),
                )
            ),
            "book": lambda: "Book",
            "incollection": lambda: "Book chapter ({0})".format(
                normalize(self.reference.bibliography_values.get("booktitle", ""))
            ),
            "phdthesis": lambda: "PhD thesis",
            "mastersthesis": lambda: "Master's thesis",
            "techreport": lambda: "Techreport",
            "misc": lambda: "Misc ({0})".format(
                normalize(self.reference.bibliography_values.get("howpublished", ""))
            ),
        }
        reference_type = recognized_reference_type_fns.get(
            self.reference.bibliography_values.get("ENTRYTYPE", None), lambda: "Other"
        )()

        # Remove trailing "()" if present.
        if reference_type.endswith("()"):
            return reference_type[:-3]

        return reference_type

    def compose(self) -> ComposeResult:
        year = self.reference.year if self.reference else 0
        title = self.reference.title if self.reference else ""
        author = self.reference.author if self.reference else ""
        reference_type = self.__get_reference_type() if self.reference else ""
        full_reference = (
            "\n".join(
                op.transform_reference_dict_to_lines(self.reference.bibliography_values)
            )
            if self.reference
            else ""
        )
        if self.show_yeartitle:
            yield YearTitleDisplay(year, title, id="yeartitle")
            yield Label(reference_type, id="type")
        if self.show_author:
            yield Label(author, id="author")
        if self.show_full_reference:
            yield Label(full_reference, id="full-reference")
        if self.clickable:
            yield Center(Button("Choose", id="choose"))
        self.__composed = True

    def watch_reference(self) -> None:
        if not self.__composed:
            return

        if self.reference is None:
            return

        if self.show_yeartitle:
            self.query_one(
                "#yeartitle", expect_type=YearTitleDisplay
            ).year = self.reference.year
            self.query_one(
                "#yeartitle", expect_type=YearTitleDisplay
            ).title = self.reference.title
            self.query_one("#type", expect_type=Label).update(
                self.__get_reference_type()
            )
        if self.show_author:
            self.query_one("#author", expect_type=Label).update(self.reference.author)
        from rich.syntax import Syntax
        if self.show_full_reference:
            bibtex = "\n".join(
                    op.transform_reference_dict_to_lines(
                        self.reference.bibliography_values
                    )
                )
            self.query_one("#full-reference", expect_type=Label).update(
                Syntax(bibtex, "bibtex", theme="material", line_numbers=False,
                       word_wrap=True, dedent=True)
            )


class ReferencePicker(Static):
    available_references: Reactive[list[Reference]] = reactive([])
    current_reference: Reactive[Optional[Reference]] = reactive(None)
    show_chosen_reference_details: Reactive[bool] = reactive(True)
    __composed = False
    can_focus_children = True
    can_focus = True

    def __init__(
        self,
        get_next_choice_task_fn: Callable[
            [],
            Optional[
                Union[
                    ReferenceChoiceTask,
                    Coroutine[Any, Any, Optional[ReferenceChoiceTask]],
                ]
            ],
        ],
        get_choice_fn: Callable[[ReferenceChoice], None],
        show_chosen_reference_details: bool = True,
        **kwargs,
    ):
        Placeholder
        super().__init__(**kwargs)
        self.get_next_choice_task_fn = get_next_choice_task_fn
        self.get_choice_fn = get_choice_fn
        self.show_chosen_reference_details = show_chosen_reference_details

    async def _refresh_choice_task(self) -> None:
        choice_task = await await_me_maybe(self.get_next_choice_task_fn)
        if choice_task is not None:
            self.available_references = choice_task.available_references
            self.current_reference = choice_task.current_reference

    async def _save_choice(self, reference: Reference) -> None:
        if self.current_reference is None:
            raise RuntimeError("No current reference to compare to.")

        self.get_choice_fn(ReferenceChoice(self.current_reference, reference))
        await await_me_maybe(self._refresh_choice_task)

    def compose(self) -> ComposeResult:
        with Middle(classes="referencepicker-column"):
            yield Label("Current Reference", classes="reference-picker-column-title")
            yield ReferenceDisplay(
                None, clickable=False, id="current-reference", show_full_reference=True
            )
        with Widget(classes="referencepicker-column referencepicker-center-column"):
            yield Label(
                "Alternative References", classes="reference-picker-column-title"
            )
            yield ScrollableContainer(
                *[
                    ReferenceDisplay(rf, click_callback=self._save_choice)
                    for rf in self.available_references
                ],
                id="available-references",
            )
        with Middle(
            classes="referencepicker-column", id="chosen-reference-column"
        ) as col:
            yield Label(
                "Details on Chosen Reference", classes="reference-picker-column-title"
            )
            yield ReferenceDisplay(
                None,
                clickable=False,
                id="chosen-reference",
                show_full_reference=True,
                show_yeartitle=False,
                show_author=False,
            )
            col.display = self.show_chosen_reference_details
        self.__composed = True

    def on_mount(self) -> None:
        loop = asyncio.get_event_loop()
        loop.create_task(self._refresh_choice_task())
        self.focus()

    def watch_current_reference(self) -> None:
        if not self.__composed:
            return
        current = self.query_one("#current-reference", expect_type=ReferenceDisplay)
        current.reference = self.current_reference

    def watch_show_chosen_reference_details(self) -> None:
        if not self.__composed:
            return
        current = self.query_one("#chosen-reference-column", expect_type=Middle)
        current.display = self.show_chosen_reference_details

    def on_descendant_focus(self, event: events.DescendantFocus):
        if isinstance(event._sender.parent.parent, ReferenceDisplay):
            chosen_reference = event._sender.parent.parent.reference
            display = self.query_one("#chosen-reference", expect_type=ReferenceDisplay)
            display.reference = chosen_reference

            self.query_one("#chosen-reference-column").visible = True

    def on_key(self, event: events.Key) -> None:
        if event.key in [str(d) for d in range(9)]:
            idx = int(event.key) - 1
            if 0 <= idx < len(self.available_references):
                rfd = self.query_one("#available-references").children[idx]
                try:
                    button = rfd.query_one("#choose", expect_type=Button)
                    if button.has_focus:
                        button.action_press()
                    else:
                        button.focus(True)
                except NoMatches:
                    # This can happen if the user presses a button while the element
                    # is being composed and the button has not been added yet.
                    pass
        elif event.key == "up":
            rfds = self.query_one("#available-references").children
            current_idx = len(rfds)
            for idx, rfd in enumerate(rfds):
                if rfd.query_one("#choose").has_focus:
                    current_idx = idx
                    break
            rfds[(current_idx - 1) % len(rfds)].query_one("#choose").focus()
        elif event.key == "down":
            rfds = self.query_one("#available-references").children
            current_idx = -1
            for idx, rfd in enumerate(rfds):
                if rfd.query_one("#choose").has_focus:
                    current_idx = idx
                    break
            rfds[(current_idx + 1) % len(rfds)].query_one("#choose").focus()

    def watch_available_references(self) -> None:
        if not self.__composed:
            return

        self.query_one("#chosen-reference-column").visible = False

        references = self.query_one("#available-references")
        if references:
            while len(references.children) > 0:
                references.children[0].remove()

            rfds = []
            for idx, rf in enumerate(self.available_references):
                rfd = ReferenceDisplay(rf, click_callback=self._save_choice)
                if idx > 0:
                    rfd.border_title = str(idx + 1)
                else:
                    # First element is the current reference; highlight it.
                    rfd.border_title = f"{idx + 1} (Current)"
                rfds.append(rfd)
            references.mount(*rfds)


class ManualReferenceUpdaterApp(App):
    BINDINGS = [
        ("m", "toggle_dark", "Toggle dark mode"),
        ("d", "toggle_reference_picker_details", "Toggle details of chosen reference"),
        ("s", "stop", "Stop selection"),
    ]
    CSS_PATH = "manual_reference_updater.css"

    TITLE = "Reference Updater"

    def __init__(
        self,
        choice_task_iterator: Union[
            Generator[ReferenceChoiceTask, None, None],
            AsyncGenerator[ReferenceChoiceTask, None],
        ],
        n_tasks: Optional[int],
    ):
        super().__init__()
        self.choice_task_iterator = choice_task_iterator
        self.choices: list[ReferenceChoice] = []
        self.n_tasks = n_tasks

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""

        async def get_next_choice_task_fn() -> Optional[ReferenceChoiceTask]:
            try:
                choice_task = await anext_maybe(self.choice_task_iterator)
                try:
                    await self.query_one("#loadingindicator").remove()
                    self.query_one("#referencepicker").visible = True
                    self.query_one("#progressbar").visible = True
                except NoMatches:
                    pass
            except (StopAsyncIteration, StopIteration):
                self.exit(self.choices)
                return None
            else:
                return choice_task

        def get_choice_fn(reference_choice: ReferenceChoice) -> None:
            self.choices.append(reference_choice)
            self.query_one("#progressbar", expect_type=ProgressBar).update(
                progress=len(self.choices)
            )

        pbar = ProgressBar(id="progressbar", total=self.n_tasks)
        pbar.visible = False
        yield pbar
        yield Footer()
        yield LoadingIndicator(id="loadingindicator")
        rp = ReferencePicker(
            get_next_choice_task_fn, get_choice_fn, id="referencepicker"
        )
        rp.visible = False
        yield rp

    def action_toggle_reference_picker_details(self):
        """An action to toggle whether the details of the chosen reference are shown."""
        rp = self.query_one("#referencepicker", expect_type=ReferencePicker)
        rp.show_chosen_reference_details = not rp.show_chosen_reference_details

    def action_toggle_dark(self) -> None:
        """An action to toggle dark mode."""
        self.dark = not self.dark

    def action_stop(self) -> None:
        """An action to stop the app."""
        self.exit(self.choices)

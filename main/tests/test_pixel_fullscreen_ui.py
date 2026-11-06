from types import SimpleNamespace
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_midi_ui import window,pump


def test_f11_and_escape_restore_a_maximized_window_with_focus_on_a_child(window):
    app,owner=window;owner.pages.setCurrentIndex(9);owner.showMaximized();app.processEvents()
    QTest.keyClick(owner.pixel_page.fullscreen_button,Qt.Key.Key_F11)
    assert owner.isFullScreen() and not owner.sidebar.isVisible()
    QTest.keyClick(owner.pixel_page.start,Qt.Key.Key_Escape)
    assert not owner.isFullScreen() and owner.isMaximized() and owner.sidebar.isVisible()
    QTest.keyClick(owner.pixel_page.fullscreen_button,Qt.Key.Key_F11)
    owner.pixel_page.fullscreen_button.click();assert not owner.isFullScreen()


def test_chromium_canvas_fullscreen_is_redirected_to_an_exitable_native_window(window):
    _,owner=window;owner.pages.setCurrentIndex(9);calls=[]
    request=SimpleNamespace(reject=lambda:calls.append('reject'),toggleOn=lambda:True)
    owner.pixel_page._fullscreen(request);assert calls==['reject'] and owner.isFullScreen()
    owner.pixel_page._fullscreen(SimpleNamespace(reject=lambda:calls.append('exit'),toggleOn=lambda:False))
    assert not owner.isFullScreen() and owner.sidebar.isVisible()


def test_navigation_away_from_pixel_studio_leaves_fullscreen(window):
    _,owner=window;owner.pages.setCurrentIndex(9);owner.pixel_page.toggle_fullscreen();owner._navigate(2)
    assert not owner.isFullScreen() and owner.sidebar.isVisible() and owner.subtitle.isVisible()

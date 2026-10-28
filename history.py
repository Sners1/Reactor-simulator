"""Экран «История первых реакторов» — три вехи ядерной энергетики."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from menu import MENU_QSS, _header_frame


HISTORY_QSS = MENU_QSS + """
QTextBrowser#historyBody {
    background-color: #0b0e0b;
    color: #b9d9b9;
    border: 1px solid #24361f;
    border-radius: 6px;
    font-size: 13px;
}
QScrollBar:vertical {
    background: #0a0c0a;
    width: 10px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2c4a2c;
    border-radius: 5px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover {
    background: #3f6a3f;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
"""


HISTORY_HTML = """<html><body>
<h2 style='color:#9dff9d; margin-bottom:2px;'>CHICAGO PILE-1 · 1942</h2>
<p style='color:#6d8a6d; margin-top:0;'>Первый в мире искусственный ядерный реактор</p>
<p>2 декабря 1942 года под трибунами стадиона Чикагского университета заработала «Чикагская поленница-1». Её собрали из штабеля графитовых блоков, внутри которых лежали куски природного урана: графит замедлял нейтроны, уран поддерживал цепную реакцию, а мощность регулировали кадмиевыми стержнями, которые вдвигали в кладку вручную.</p>
<p>В игре вы управляете ровно тем же самым: стержни поглощают нейтроны и задают реактивность, а охлаждение уносит тепло из активной зоны. Опустили стержни — мощность падает, подняли — растёт. Поэтому первым делом оператор учится двигать стержни на 1–2 %, и только потом трогает насосы.</p>

<h2 style='color:#9dff9d; margin-bottom:2px;'>ОБНИНСКАЯ АЭС · 1954</h2>
<p style='color:#6d8a6d; margin-top:0;'>Первая в мире промышленная атомная электростанция</p>
<p>В Обнинске Калужской области запустили первую АЭС, работавшую на сеть. Это был канальный уран-графитовый реактор: каждый тепловыделяющий элемент стоял в собственном канале, вода кипела прямо в каналах и шла на турбину. Схема позволяла наращивать мощность, добавляя каналы, а не переделывая весь корпус целиком.</p>
<p>Сборка реактора из модулей в Верфи перекликается с тем, как инженеры собирали первые энергоблоки: корпус, каналы, теплоноситель, контур охлаждения и турбина проектировались и монтировались по отдельности, а на площадке стыковались в единый блок. Чем аккуратнее собрана связка модулей, тем выше эффективность — ровно как у первых энергоблоков, где качество стыковки и запас прочности решали всё.</p>

<h2 style='color:#9dff9d; margin-bottom:2px;'>РБМК И ЧЕРНОБЫЛЬ · 1986</h2>
<p style='color:#6d8a6d; margin-top:0;'>Реактор большой мощности канальный</p>
<p>РБМК — прямой наследник обнинской схемы: графитовый замедлитель, сотни каналов с водой, кипение прямо в активной зоне. У такой схемы есть опасная особенность — положительный паровой коэффициент реактивности. Пузыри пара вытесняют воду, вода замедляет нейтроны, и чем больше пара, тем больше нейтронов возвращается в реакцию. Мощность растёт, пара становится ещё больше, и реактор разгоняется сам.</p>
<p>В нашей игре этот эффект проработан специально: при кипении теплоносителя паросодержание добавляет реактивность, поэтому за температурой и расходом нужно следить постоянно, а не только на старте.</p>
<p>Вторая критическая вещь — ксеноновое отравление. Ксенон-135 накапливается после работы на мощности и «съедает» реактивность: стрелка мощности ползёт вниз сама, хотя вы ничего не трогали. Оператор в 1986 году начал выводить стержни, чтобы удержать мощность, и загнал реактор в состояние, где запас реактивности уже не контролировался.</p>
<p>Третья — АЗ-5, аварийная защита (SCRAM). Кнопка, которая должна мгновенно заглушить реактор, в ту ночь сработала как спусковой крючок: графитовые вытеснители на концах стержней, заходя в активную зону, сначала добавили реактивность. Отсюда правило, которое действует и в игре: аварийная остановка — это последний рубеж, а не инструмент управления мощностью, и доводить до неё лучше не надо.</p>
</body></html>"""


class HistoryWindow(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("РЕАКТОР — история первых реакторов")
        self.resize(900, 640)
        self.setStyleSheet(HISTORY_QSS)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(16)
        root.addWidget(
            _header_frame("ИСТОРИЯ РЕАКТОРОВ", "ОТ ГРАФИТОВОЙ ПОЛЕННИЦЫ ДО РБМК")
        )

        body = QTextBrowser()
        body.setObjectName("historyBody")
        body.setOpenExternalLinks(False)
        body.setHtml(HISTORY_HTML)
        root.addWidget(body, 1)

        back = QPushButton("НАЗАД")
        back.setObjectName("menuButtonSmall")
        back.clicked.connect(self.back_requested.emit)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addStretch(1)
        row.addWidget(back)
        holder = QWidget()
        holder.setLayout(row)
        root.addWidget(holder)

        mark = QLabel('@Sners1')
        mark.setAlignment(Qt.AlignmentFlag.AlignRight)
        mark.setStyleSheet('color: rgba(170, 140, 255, 90); font-size: 10px; letter-spacing: 1px;')
        root.addWidget(mark)

from PySide6.QtWidgets import QApplication, QStyle
from PySide6.QtGui import QIcon
from PySide6.QtCore import QResource

def get_icon(name: str) -> QIcon:
    st = QApplication.style()
    mp = {
        "dashboard": QStyle.SP_ComputerIcon,
        "journal": QStyle.SP_FileIcon,
        "grand_livre": QStyle.SP_DirIcon,
        "bilan": QStyle.SP_DialogApplyButton,
        "resultat": QStyle.SP_DialogOkButton,
        "comptes": QStyle.SP_DirHomeIcon,
        "revision": getattr(QStyle, "SP_BrowserReload", QStyle.SP_BrowserStop),
        "parametres": QStyle.SP_FileDialogDetailedView,
        "scrap": QStyle.SP_MediaPlay,
        "profil_scraping": QStyle.SP_FileDialogInfoView,
        "galerie": QStyle.SP_DirOpenIcon,
    }
    if name in mp:
        return st.standardIcon(mp[name])
    path = f":/icons/{name}.svg"
    if QResource.registerResource:
        return QIcon(path)
    return QIcon()

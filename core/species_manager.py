import json

from core import app_paths

from PySide6.QtWidgets import (
    QColorDialog,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
)


CONFIG_NAME = "species_config.json"


def config_path():
    """Per-user species database, seeded from the one shipped with the app."""
    return app_paths.config_file(CONFIG_NAME)


def load_species():
    path = config_path()
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("species_config.json doit contenir une liste.")

    species_list = []
    for item in data:
        if not isinstance(item, dict):
            continue

        common_name = str(item.get("common_name", "")).strip()
        scientific_name = str(item.get("scientific_name", "")).strip()
        family = str(item.get("family", "")).strip()
        color = str(item.get("color", "#CCCCCC")).strip()
        active = bool(item.get("active", True))

        if not common_name:
            continue

        species_list.append(
            {
                "common_name": common_name,
                "scientific_name": scientific_name,
                "family": family,
                "color": color,
                "active": active,
            }
        )

    return species_list


def save_species(species_list):
    with open(config_path(), "w", encoding="utf-8") as f:
        json.dump(species_list, f, ensure_ascii=False, indent=2)


class SpeciesManagerDialog(QDialog):
    def __init__(self, species_list, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gérer les espèces")
        self.resize(720, 420)

        self.species_list = [dict(s) for s in species_list]
        self.current_color = "#CCCCCC"

        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        main_layout = QHBoxLayout()

        self.list_widget = QListWidget()
        self.list_widget.itemSelectionChanged.connect(self._load_selected_species)

        left_layout = QVBoxLayout()
        left_layout.addWidget(self.list_widget)

        right_widget = QWidget()
        form_layout = QFormLayout()

        self.common_name_input = QLineEdit()
        self.scientific_name_input = QLineEdit()
        self.family_input = QLineEdit()
        self.color_label = QLabel(self.current_color)

        self.choose_color_button = QPushButton("Choisir couleur")
        self.choose_color_button.clicked.connect(self._choose_color)

        self.add_button = QPushButton("Ajouter nouvelle")
        self.add_button.clicked.connect(self._add_species)

        self.update_button = QPushButton("Mettre à jour")
        self.update_button.clicked.connect(self._update_species)

        self.delete_button = QPushButton("Supprimer")
        self.delete_button.clicked.connect(self._delete_species)

        self.save_button = QPushButton("Enregistrer et fermer")
        self.save_button.clicked.connect(self.accept)

        form_layout.addRow("Nom commun :", self.common_name_input)
        form_layout.addRow("Nom scientifique :", self.scientific_name_input)
        form_layout.addRow("Famille :", self.family_input)
        form_layout.addRow("Couleur :", self.color_label)
        form_layout.addRow("", self.choose_color_button)
        form_layout.addRow("", self.add_button)
        form_layout.addRow("", self.update_button)
        form_layout.addRow("", self.delete_button)
        form_layout.addRow("", self.save_button)

        right_widget.setLayout(form_layout)

        main_layout.addLayout(left_layout, 2)
        main_layout.addWidget(right_widget, 3)
        self.setLayout(main_layout)

    def _refresh_list(self):
        self.list_widget.clear()
        for species in self.species_list:
            label = f"{species['common_name']} — {species['scientific_name']}"
            self.list_widget.addItem(QListWidgetItem(label))

    def _load_selected_species(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.species_list):
            return

        species = self.species_list[row]
        self.common_name_input.setText(species["common_name"])
        self.scientific_name_input.setText(species["scientific_name"])
        self.family_input.setText(species["family"])
        self.current_color = species["color"]
        self.color_label.setText(self.current_color)

    def _choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.current_color = color.name()
            self.color_label.setText(self.current_color)

    def _add_species(self):
        common_name = self.common_name_input.text().strip()
        scientific_name = self.scientific_name_input.text().strip()
        family = self.family_input.text().strip()

        if not common_name:
            QMessageBox.warning(self, "Nom manquant", "Le nom commun est obligatoire.")
            return

        self.species_list.append(
            {
                "common_name": common_name,
                "scientific_name": scientific_name,
                "family": family,
                "color": self.current_color,
                "active": True,
            }
        )
        self._refresh_list()

    def _update_species(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.species_list):
            QMessageBox.warning(self, "Aucune sélection", "Sélectionne une espèce.")
            return

        common_name = self.common_name_input.text().strip()
        scientific_name = self.scientific_name_input.text().strip()
        family = self.family_input.text().strip()

        if not common_name:
            QMessageBox.warning(self, "Nom manquant", "Le nom commun est obligatoire.")
            return

        self.species_list[row] = {
            "common_name": common_name,
            "scientific_name": scientific_name,
            "family": family,
            "color": self.current_color,
            "active": True,
        }
        self._refresh_list()
        self.list_widget.setCurrentRow(row)

    def _delete_species(self):
        row = self.list_widget.currentRow()
        if row < 0 or row >= len(self.species_list):
            QMessageBox.warning(self, "Aucune sélection", "Sélectionne une espèce.")
            return

        del self.species_list[row]
        self._refresh_list()

    def get_species_list(self):
        return self.species_list
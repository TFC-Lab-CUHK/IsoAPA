"""Canonical and common-name matching for species exposed by IsoAPA."""
from __future__ import annotations

import re
import unicodedata
from typing import Optional


# Common English names are intentionally curated rather than resolved through
# a runtime taxonomy service, keeping public search deterministic and offline.
COMMON_SPECIES_ALIASES: dict[str, tuple[str, ...]] = {
    "Acyrthosiphon_pisum": ("pea aphid",),
    "Aedes_aegypti": ("yellow fever mosquito", "dengue mosquito"),
    "Aegilops_tauschii": ("tausch's goatgrass", "goatgrass"),
    "Anas_platyrhynchos": ("mallard",),
    "Anopheles_gambiae": ("african malaria mosquito", "malaria mosquito"),
    "Apis_mellifera": ("honey bee", "western honey bee"),
    "Arabidopsis_thaliana": ("arabidopsis", "thale cress", "a. thaliana"),
    "Arachis_hypogaea": ("peanut", "groundnut"),
    "Bombyx_mori": ("silkworm",),
    "Bos_grunniens": ("yak",),
    "Bos_taurus": ("cattle", "cow"),
    "Branchiostoma_floridae": ("florida lancelet", "amphioxus"),
    "Brassica_napus": ("rapeseed", "canola"),
    "Brassica_oleracea": ("cabbage",),
    "Brassica_rapa": ("field mustard", "turnip"),
    "Brugia_malayi": ("malayan filarial worm", "filarial worm"),
    "Caenorhabditis_elegans": ("c. elegans", "nematode"),
    "Callithrix_jacchus": ("common marmoset", "marmoset"),
    "Camellia_sinensis": ("tea plant", "tea"),
    "Candida_albicans": ("candida",),
    "Cannabis_sativa": ("cannabis", "hemp"),
    "Capra_hircus": ("goat",),
    "Cavia_porcellus": ("guinea pig",),
    "Chlamydomonas_reinhardtii": ("chlamydomonas", "green alga"),
    "Chlorocebus_sabaeus": ("african green monkey", "green monkey"),
    "Chrysemys_picta": ("painted turtle",),
    "Cicer_arietinum": ("chickpea", "garbanzo"),
    "Ciona_intestinalis": ("sea squirt",),
    "Citrus_sinensis": ("sweet orange", "orange"),
    "Columba_livia": ("rock pigeon", "pigeon"),
    "Coprinopsis_cinerea": ("ink cap mushroom", "ink cap"),
    "Coturnix_japonica": ("japanese quail", "quail"),
    "Cricetulus_griseus": ("chinese hamster", "hamster"),
    "Cucumis_melo": ("melon", "muskmelon"),
    "Cucumis_sativus": ("cucumber",),
    "Danio_rerio": ("zebrafish",),
    "Daphnia_magna": ("water flea",),
    "Drosophila_melanogaster": ("fruit fly", "d. melanogaster"),
    "Drosophila_suzukii": ("spotted wing drosophila", "d. suzukii"),
    "Entamoeba_histolytica": ("dysentery amoeba", "amoeba"),
    "Equus_caballus": ("horse",),
    "Eriocheir_sinensis": ("chinese mitten crab", "mitten crab"),
    "Eucalyptus_grandis": ("rose gum", "eucalyptus"),
    "Gallus_gallus": ("chicken",),
    "Gorilla_gorilla": ("western gorilla", "gorilla"),
    "Gossypium_hirsutum": ("upland cotton", "cotton"),
    "Gossypium_raimondii": ("raimond's cotton", "cotton"),
    "Heterocephalus_glaber": ("naked mole rat",),
    "Heterodera_glycines": ("soybean cyst nematode",),
    "Hordeum_vulgare": ("barley",),
    "Human": ("human", "man"),
    "Hydra_vulgaris": ("hydra",),
    "Limulus_polyphemus": ("atlantic horseshoe crab", "horseshoe crab"),
    "Lottia_gigantea": ("owl limpet", "limpet"),
    "Lotus_japonicus": ("japanese trefoil", "lotus"),
    "Macaca_fascicularis": ("crab-eating macaque", "cynomolgus monkey"),
    "Macaca_mulatta": ("rhesus macaque", "rhesus monkey"),
    "Malus_domestica": ("apple", "domestic apple"),
    "Monodelphis_domestica": ("gray short-tailed opossum", "opossum"),
    "Mouse": ("mouse", "house mouse"),
    "Naja_naja": ("indian cobra", "cobra"),
    "Nasonia_vitripennis": ("jewel wasp",),
    "Nelumbo_nucifera": ("sacred lotus", "lotus"),
    "Nematostella_vectensis": ("starlet sea anemone", "sea anemone"),
    "Nicotiana_tabacum": ("tobacco",),
    "Octopus_bimaculoides": ("california two-spot octopus", "two-spot octopus"),
    "Octopus_vulgaris": ("common octopus", "octopus"),
    "Olea_europaea": ("olive", "olive tree"),
    "Oncorhynchus_mykiss": ("rainbow trout", "trout"),
    "Oreochromis_niloticus": ("nile tilapia", "tilapia"),
    "Oryctolagus_cuniculus": ("rabbit", "european rabbit"),
    "Oryza_sativa": ("rice", "asian rice"),
    "Oryzias_latipes": ("medaka", "japanese rice fish"),
    "Ovis_aries": ("sheep",),
    "Pan_troglodytes": ("chimpanzee", "chimp"),
    "Penaeus_monodon": ("giant tiger prawn", "tiger shrimp"),
    "Penaeus_vannamei": ("whiteleg shrimp", "pacific white shrimp"),
    "Phodopus_sungorus": ("siberian hamster", "djungarian hamster"),
    "Plasmodium_falciparum": ("human malaria parasite", "malaria parasite"),
    "Plasmodium_yoelii": ("rodent malaria parasite", "malaria parasite"),
    "Pleurodeles_waltl": ("iberian ribbed newt", "ribbed newt"),
    "Pongo_abelii": ("sumatran orangutan", "orangutan"),
    "Populus_trichocarpa": ("black cottonwood", "poplar"),
    "Rattus_norvegicus": ("rat", "norway rat", "brown rat"),
    "Saccharomyces_cerevisiae": ("baker's yeast", "budding yeast", "s. cerevisiae"),
    "Salmo_salar": ("atlantic salmon", "salmon"),
    "Schizosaccharomyces_pombe": ("fission yeast", "s. pombe"),
    "Solanum_lycopersicum": ("tomato",),
    "Solanum_tuberosum": ("potato",),
    "Sorghum_bicolor": ("sorghum",),
    "Spinacia_oleracea": ("spinach",),
    "Sus_scrofa": ("pig", "wild boar", "swine"),
    "Taeniopygia_guttata": ("zebra finch",),
    "Toxoplasma_gondii": ("toxoplasma",),
    "Triticum_aestivum": ("bread wheat", "wheat"),
    "Vitis_vinifera": ("grape", "grapevine", "wine grape"),
    "Xenopus_laevis": ("african clawed frog", "clawed frog"),
    "Xenopus_tropicalis": ("western clawed frog", "clawed frog"),
    "Zea_mays": ("maize", "corn"),
}


def normalize_species_term(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).casefold()
    text = text.replace("_", " ").replace("-", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def species_aliases(name: str, latin_name: Optional[str] = None) -> list[str]:
    aliases = list(COMMON_SPECIES_ALIASES.get(name, ()))
    latin_parts = str(latin_name or "").split()
    if len(latin_parts) >= 2:
        aliases.append(f"{latin_parts[0][0]}. {' '.join(latin_parts[1:])}")

    seen: set[str] = set()
    result: list[str] = []
    for alias in aliases:
        key = normalize_species_term(alias)
        if key and key not in seen:
            seen.add(key)
            result.append(alias)
    return result


def species_search_terms(name: str, latin_name: Optional[str] = None) -> list[str]:
    values = [name, str(name or "").replace("_", " "), latin_name or ""]
    values.extend(species_aliases(name, latin_name))
    return [term for value in values if (term := normalize_species_term(value))]


def species_match_rank(
    query: object, name: str, latin_name: Optional[str] = None
) -> Optional[int]:
    normalized_query = normalize_species_term(query)
    if not normalized_query:
        return None

    terms = species_search_terms(name, latin_name)
    if normalized_query in terms:
        return 0
    if any(term.startswith(normalized_query) for term in terms):
        return 1
    if any(normalized_query in term for term in terms):
        return 2
    return None

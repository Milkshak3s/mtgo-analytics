import click
from datetime import datetime, timedelta
import json
import os
import shutil
import subprocess


WRITEFILE = "filelist.txt"
RULEFILE = "archetype_rules.json"


def load_file_json(filename):
    data = {}
    with open(filename, "r") as f:
        data = json.load(f)
    return data


def load_cache_filepaths():
    return load_file_json(WRITEFILE)


def load_working_filepaths():
    return load_file_json(f"{WRITEFILE}.working")
    

def load_archetype_ruleset():
    return load_file_json(RULEFILE)



def matches(cardlist, rule):
    for match in rule["matches"]:
        if match["count"] > 0:
            if cardlist.count(match["card"].lower()) < match["count"]:
                return False
        else:
            if match["card"].lower() in cardlist:
                return False
    return True


def check_rule_matches(deck):
    """Returns a list of matching rules"""
    rules = load_archetype_ruleset()
    cardlist = []
    for card in deck["Mainboard"]:
        for x in range(card["Count"]):
            cardlist.append(card["CardName"].lower())

    matching = []
    for rule in rules:
        if matches(cardlist, rule):
            matching.append(rule)
    return matching

@click.group()
def cli():
    pass

def f_get_filelist(after_date, format):
    """Function for get_filelist command"""
    date = datetime.fromisoformat(after_date)

    cachedir = './MTGODecklistCache/Tournaments'
    mut_date = datetime.date(date)
    files = []
    for subdir in os.listdir(cachedir):
        while mut_date <= datetime.date(datetime.now()):
            month = mut_date.strftime("%m")
            day = mut_date.strftime("%d")
            path = f'{cachedir}/{subdir}/{mut_date.year}/{month}/{day}'
            click.echo(path)
            if os.path.isdir(path):
                click.echo(f"2{path}")
                dirlist = os.listdir(path)
                for filename in dirlist:
                    if format in filename:
                        files.append(f'{path}/{filename}')
                
            mut_date = mut_date + timedelta(days=1)
        mut_date = datetime.date(date)

    with open(WRITEFILE, "w") as f:
        f.write(json.dumps(files))
    click.echo(f"Written to '{WRITEFILE}'")

@cli.command()
@click.argument('after_date', nargs=1, type=str)
@click.argument('format', nargs=1, type=str)
def get_filelist(after_date, format):
    """Generate a list of files after a certain date with the format YYYY-MM-DD"""
    return f_get_filelist(after_date, format)

def f_copy_working_files():
    """Function for copy_working_files command"""
    filepaths = load_cache_filepaths()
    
    # holy fuck
    new_filepaths = []
    for filepath in filepaths:
        normpath = os.path.normpath(filepath)
        splitpath = normpath.split(os.sep)
        splitpath[0] = "MTGODecklistCacheModified"
        new_path = os.sep.join(splitpath)
        os.makedirs(os.sep.join(splitpath[:-1]), exist_ok=True)
        shutil.copyfile(filepath, new_path)
        new_filepaths.append(new_path)

    with open(f"{WRITEFILE}.working", "w") as f:
        f.write(json.dumps(new_filepaths))
    click.echo(new_filepaths)

@cli.command()
def copy_working_files():
    """Copy working files from 'filelist.txt" into the 'MTGODecklistCacheModified' dir"""
    return f_copy_working_files()

    with open(f"{WRITEFILE}.working", "w") as f:
        f.write(json.dumps(new_filepaths))
    click.echo(new_filepaths)


def f_enrich():
    """Function for enrich command"""
    filepaths = load_working_filepaths()

    for filepath in filepaths:
        click.echo(f"On: {filepath}")
        data = {}
        with open(filepath, "r") as f:
            data = json.load(f)
        deck_count = len(data["Decks"])
        data["DeckCount"] = deck_count
        with open(filepath, "w+") as f:
            json.dump(data, f)

@cli.command()
def enrich():
    """Enrich working json files"""
    return f_enrich()

@cli.command()
@click.argument('after_date', nargs=1, type=str)
@click.argument('format', nargs=1, type=str)
@click.option("--update", "-u", is_flag=True)
def setup(after_date, format, update):
    """Run all setup commands (get-filelist, copy-working-files, enrich)"""
    if update:
        subprocess.run(["cd", "MTGODecklistCache"], shell=True)
        subprocess.run(["git", "pull"])
        subprocess.run(["cd", ".."], shell=True)
    f_get_filelist(after_date, format)
    f_copy_working_files()
    f_enrich()
    click.echo("Setup complete")


def format_decklist(deck):
    deck_string = "Mainboard:\n"
    for card in deck["Mainboard"]:
        deck_string += f"  {str(card['Count'])} {card['CardName']}\n"
    deck_string += "Sideboard:\n"
    for card in deck["Sideboard"]:
        deck_string += f"  {str(card['Count'])} {card['CardName']}\n"
    return deck_string

@cli.command()
@click.option("--silent", "-s", is_flag=True)
def check_rules(silent):
    """Run working files against the rules in 'archetype_rules.json'"""
    filepaths = load_working_filepaths()
    count = 0
    for filepath in filepaths:
        data = load_file_json(filepath)
        for deck in data["Decks"]:
            count += 1
            rule_matches = check_rule_matches(deck)
            archetypes = set(list(map(lambda x : x["archetype"], rule_matches)))
            if len(archetypes) == 1:
                if not silent:
                    click.echo(f"{rule_matches[0]['archetype']}")
                deck["Archetype"] = rule_matches[0]["archetype"]
            if len(archetypes) > 1:
                click.echo(f"Multiple archetypes matched (disambiguation required): {list(map(lambda x : x['name'], rule_matches))}")
                click.echo(f"===Decklist===\n")
                click.echo(format_decklist(deck))
                with open(filepath, "w+") as f: #TODO -- this is big slops, find a better way to handle escaping
                    json.dump(data, f)
                return
            if len(archetypes) < 1:
                click.echo(f"No archetypes matched (additional decklist rule required)")
                click.echo(f"===Decklist===\n")
                click.echo(format_decklist(deck))
                with open(filepath, "w+") as f:
                    json.dump(data, f)
                return
        with open(filepath, "w+") as f:
            json.dump(data, f)
    click.echo(f"\nMatched archetypes for {count} decks in {len(filepaths)} files")


@cli.command()
def get_archetypes():
    """Display all archetype annotations"""
    pass

def to_rule(card_list):
    rule = []
    sanitized_list = dict(card_list)
    for card in sanitized_list:
        card_dict = {}
        card_dict["card"] = card
        card_dict["count"] = int(sanitized_list[card])
        rule.append(card_dict)
    return rule


@cli.command()
@click.argument('name', nargs=1, type=str)
@click.argument('archetype', nargs=1, type=str)
@click.argument('cards', nargs=-1, type=str)
def add_rule(name, archetype, cards):
    """Introduce the provided rule to the ruleset in 'archetype_rules.json'. If the rule already exists, overwrite it"""
    rules = load_archetype_ruleset()
    cards = list(map(lambda x : x.split(':'), cards))
    new_rule = to_rule(cards)
    new = True
    for rule in rules:
        if rule["name"] == name:
            rule["archetype"] = archetype
            rule["matches"] = new_rule
            new = False
    if new:
        rules.append({
            "name" : name,
            "archetype" : archetype,
            "matches" : new_rule
            })
    with open(RULEFILE, "w") as f:
            json.dump(rules, f)

@cli.command()
@click.argument('name', nargs=1, type=str)
def delete_rule(name):
    """Remove the specified rule from the ruleset in 'archetype_rules.json', if found"""
    rules = load_archetype_ruleset()
    not_found = True
    for rule in rules:
        if rule["name"] == name:
            rules.remove(rule)
            not_found = False
    if not_found:
        click.echo(f"No rule with name [{name}] was found in the ruleset")
    with open(RULEFILE, "w") as f:
            json.dump(rules, f)

@cli.command()
@click.argument('name', nargs=1, type=str)
def show_rule(name):
    """Display the specified rule"""
    rules = load_archetype_ruleset()
    not_found = True
    for rule in rules:
        if rule["name"] == name:
            click.echo(f"Rule: {name}\nArchetype: {rule['archetype']}")
            for card in rule["matches"]:
                click.echo(f"  {card['count']} {card['card']}")
            return
    click.echo(f"No rule with name [{name}] was found in the ruleset")

@cli.command()
def list_rules():
    """Display the names of all rules in the ruleset"""
    rules = load_archetype_ruleset()
    rule_list = []
    for rule in rules:
        rule_list.append(rule['name'])
    rule_list.sort()
    for rule in rule_list:
        click.echo(rule)

def sort_by_values(dict):
    return sorted(list(dict.items()), key=lambda x : x[1])

@cli.command()
@click.option("--truncate", "-t", type=click.IntRange(1,))
def extract_meta(truncate):
    """Count instances of each archetype, and display the results. Optionally, the output can be truncated to only show the top n archetypes found"""
    metagame = {}
    filepaths = load_working_filepaths()
    for filepath in filepaths:
        data = load_file_json(filepath)
        for deck in data["Decks"]:
            if "Archetype" in deck and deck["Archetype"][:2] != "!!":
                metagame[deck["Archetype"]] = metagame.get(deck["Archetype"], 0) + 1
    sorted_meta = sort_by_values(metagame)
    sorted_meta.reverse()
    if truncate and truncate < len(sorted_meta) - 1:
        other_count = sum(map(lambda x : x[1], sorted_meta[truncate:]))
        sorted_meta[truncate] = ("Other", other_count)
        sorted_meta = sorted_meta[:truncate + 1]
    longest = max(map(len, metagame.keys()))
    total = sum(map(lambda x : x[1], sorted_meta))
    for archetype in sorted_meta:
        click.echo("%-*s %-4d %0.1f%%" % (longest + 2, archetype[0], archetype[1], archetype[1] / total * 100))

def search_deck(target, deck):
    for card in deck:
        if card["CardName"].lower() == target.lower():
            return card["Count"]
    return 0

@cli.command()
@click.argument('archetype', nargs=1, type=str)
@click.argument('players', nargs=-1, type=str, required=False)
def show_archetype(archetype, players):
    """Show all decklists of the specified archetype (optionally among only those belonging to the specified players)"""
    filepaths = load_working_filepaths()
    count = 0
    search_all = len(players) == 0
    for filepath in filepaths:
        data = load_file_json(filepath)
        for deck in data["Decks"]:
            if "Archetype" in deck and deck["Archetype"].lower() == archetype.lower() and (search_all or deck["Player"] in players):
                count += 1
                click.echo(f"===Decklist for {deck['Player']}===")
                click.echo(format_decklist(deck))
    players_specified_str = ""
    if not search_all:
        players_specified_str = " for player(s) " + str(list(players))
    click.echo(f"{count} total decklist(s) found matching archetype [{archetype}]" + players_specified_str)

@cli.command()
@click.argument('card', nargs=1, type=str)
@click.argument('archetypes', nargs=-1, type=str, required=False)
def search_card(card, archetypes):
    """Search each deck matching the provided archetypes (or every deck, if no archetypes are specified) for a card"""
    match_count = 0
    total_count = 0
    mainboard_average = 0
    sideboard_average = 0
    filepaths = load_working_filepaths()
    search_all = len(archetypes) == 0
    for filepath in filepaths:
        data = load_file_json(filepath)
        for deck in data["Decks"]:
            if "Archetype" in deck and (search_all or deck["Archetype"] in archetypes):
                total_count += 1
                in_mb = search_deck(card, deck["Mainboard"])
                in_sb = search_deck(card, deck["Sideboard"])
                if in_mb + in_sb > 0:
                    match_count += 1
                mainboard_average += in_mb
                sideboard_average += in_sb
    if (match_count > 0):
            mainboard_average /= match_count
            sideboard_average /= match_count
    click.echo("Found in %d out of %d decks (%0.1f%%):" % (match_count, total_count, match_count / total_count * 100))
    click.echo("  Average count in mainboards (where present): %0.2f" % (mainboard_average))
    click.echo("  Average count in sideboards (where present): %0.2f" % (sideboard_average))

if __name__ == "__main__":
    cli()

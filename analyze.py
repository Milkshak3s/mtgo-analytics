import click
from datetime import datetime, timedelta
import json
import os
import shutil


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
    return load_file_json("archetype_rules.json")



def matches(cardlist, rule):
    for match in rule["matches"]:
        if cardlist.count(match["card"].lower()) < match["count"]:
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
            matching.append(rule["name"])
    return matching

def rule_to_archetype(rule_name):
    """Returns the archetype that the given rule matches for"""
    rules = load_archetype_ruleset()
    for rule in rules:
        if rule["name"] == rule_name:
            return rule["archetype"]
    return "???"

@click.group()
def cli():
    pass


@cli.command()
@click.option("--after_date", "-a", type=str, required=True)
@click.option("--format", "-f", type=str, required=True)
def get_filelist(after_date, format):
    """Generate a list of files after a certain date with the format YYYY-MM-DD"""
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
def copy_working_files():
    """Copy working files from 'filelist.txt" into the 'MTGODecklistCacheModified' dir"""
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
def enrich():
    """Enrich working json files"""
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
def check_rules():
    """Run working files against the rules in 'archetype_rules.json'"""
    filepaths = load_working_filepaths()
    for filepath in filepaths:
        data = load_file_json(filepath)
        for deck in data["Decks"]:
            rule_matches = check_rule_matches(deck)
            click.echo(f"{rule_matches}")
            deck['Archetype'] = rule_matches
        with open(filepath, "w+") as f:
            json.dump(data, f)

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
        card_dict["count"] = sanitized_list[card]
        rule.append(card_dict)
    return rule


@cli.command()
@click.option("--name", "-n", type=str, required=True)
@click.option("--archetype", "-a", type=str, required=True)
@click.option("--card", "-c", type=(str, click.IntRange(1, 4)), required=True, multiple=True)
def add_rule(name, archetype, card):
    """Introduce the provided rule to the ruleset in 'archetype_rules.json'. If the rule already exists, overwrite it"""
    rules = load_archetype_ruleset()
    new_rule = to_rule(card)
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
def delete_rule():
    pass

def list_t_names():
    # return list of json files by date?
    pass


if __name__ == "__main__":
    cli()

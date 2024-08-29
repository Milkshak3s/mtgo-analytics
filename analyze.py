import click
from datetime import datetime, timedelta
import json
import os
import shutil


WRITEFILE = "filelist.txt"


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
    lower_deck = [s.lower() for s in cardlist.count(match["card"])]

    for match in rule["matches"]:
        if lower_deck < match["count"].lower():
            return False
    return True


def check_rule_matches(deck):
    """Returns a list of matching rules"""
    rules = load_archetype_ruleset()
    cardlist = []
    for card in deck["Mainboard"]:
        for x in range(card["Count"]):
            cardlist.append(card["CardName"])

    matching = []
    for rule in rules:
        if matches(cardlist, rule):
            matching.append(rule["name"])
    return matching


@click.group()
def cli():
    pass


@cli.command()
@click.option("--after_date", type=str, required=True)
@click.option("--format", type=str, required=True)
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


def list_t_names():
    # return list of json files by date?
    pass


if __name__ == "__main__":
    cli()

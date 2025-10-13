import typer

app = typer.Typer()

@app.command("delete")
@app.command("uninstall")
@app.command("d")
def delete(name: str):
    typer.echo(f"Deleting {name}")


if __name__ == "__main__":
    app()
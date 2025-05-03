import io, hashlib, duckdb, pandas as pd, plotly.express as px

def df_to_png(df: pd.DataFrame) -> bytes:
    """Return a PNG (in-memory bytes) from a DataFrame using a simple heuristic."""
    time_cols = [c for c in df.columns if df[c].dtype == "datetime64[ns]"]
    num_cols  = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    if time_cols and num_cols:
        fig = px.line(df, x=time_cols[0], y=num_cols[0])
    elif num_cols:
        fig = px.bar(df, x=df.columns[0], y=num_cols[0])
    else:
        fig = px.imshow(df.head(20))

    return fig.to_image(format="png", engine="kaleido")

def cache_key(question: str) -> str:
    return hashlib.sha256(question.encode()).hexdigest()

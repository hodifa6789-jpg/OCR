from src.contracts import validate_predictions,write_jsonl

def export_internal(records,expected,path):
    mapped=validate_predictions(records,expected)
    write_jsonl(path,[mapped[key] for key in sorted(mapped)])

def export_official(*args,**kwargs):
    raise NotImplementedError('Official submission specification is unresolved')

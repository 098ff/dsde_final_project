import json
import os

def validate_report(parsed_data):
    """
    Performs cross-checks and adds validation flags to the unit report.
    """
    report = {
        "unit_summary": parsed_data,
        "validation_flags": [],
        "integrity_score": 1.0
    }
    
    metadata = parsed_data.get("metadata", {})
    summary = parsed_data.get("summary_marks", {})
    
    # 1. Math Cross-Check: Good + Bad + NoVote == Attendees
    voters = metadata.get("total_voters", {}).get("val", 0)
    attendees = metadata.get("attendees", {}).get("val", 0)
    
    good = summary.get("good_ballots", {}).get("val", 0)
    bad = summary.get("bad_ballots", {}).get("val", 0)
    novote = summary.get("novote_ballots", {}).get("val", 0)
    
    total_calculated = good + bad + novote
    
    # If attendees is 0 (N/A), we compare calculated sum vs voters (which should be >=)
    if attendees > 0:
        if total_calculated != attendees:
            report["validation_flags"].append({
                "type": "MATH_MISMATCH",
                "severity": "CRITICAL",
                "message": f"Calculated ballots ({total_calculated}) do not match attendee count ({attendees})."
            })
            report["integrity_score"] -= 0.4
    else:
        report["validation_flags"].append({
            "type": "MISSING_DATA",
            "severity": "HIGH",
            "message": "Attendee count (1.2) could not be extracted reliably."
        })
        report["integrity_score"] -= 0.2

    # 2. Plausibility Check: Voters vs Attendees
    if voters < attendees:
        report["validation_flags"].append({
            "type": "PLAUSIBILITY_ERROR",
            "severity": "CRITICAL",
            "message": f"Attendees ({attendees}) cannot exceed total voters ({voters})."
        })
        report["integrity_score"] -= 0.3
        
    # Example for the pollution we saw: 1113 voters detected
    if voters > 1000: # Threshold for this small unit example
        report["validation_flags"].append({
            "type": "EXTRACTION_POLLUTION",
            "severity": "MEDIUM",
            "message": f"Voter count ({voters}) looks suspiciously high. Check for section number mergers (e.g. 1.1 + counts)."
        })
        report["integrity_score"] -= 0.1

    # 3. Confidence Check
    all_confs = []
    for section in [metadata, summary]:
        for field in section.values():
            all_confs.append(field.get("confidence", 1.0))
            if field.get("confidence", 1.0) < 0.6:
                report["validation_flags"].append({
                    "type": "LOW_CONFIDENCE",
                    "severity": "MEDIUM",
                    "field": field.get("raw", "unknown"),
                    "message": f"Value extracted with low OCR confidence ({field.get('confidence'):.2f})."
                })
    
    if all_confs:
        report["mean_confidence"] = sum(all_confs) / len(all_confs)
    else:
        report["mean_confidence"] = 0.0

    return report

def main():
    input_file = "data/processed/parsed_unit.json"
    output_file = "data/output/unit_report.json"
    
    if not os.path.exists(input_file):
        print(f"Error: {input_file} not found.")
        return
        
    with open(input_file, 'r', encoding='utf-8') as f:
        parsed_data = json.load(f)
        
    # Run validation
    report = validate_report(parsed_data)
    
    # Save
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        
    print(f"Final Unit Report saved to {output_file}")
    print(f"Integrity Score: {report['integrity_score']:.2f}")
    print(f"Validation Flags Triggered: {len(report['validation_flags'])}")
    for flag in report['validation_flags']:
        print(f" - [{flag['type']}] {flag['message']}")

if __name__ == "__main__":
    main()

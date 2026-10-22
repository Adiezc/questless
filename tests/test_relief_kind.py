from questless.contracts.model import ContractKind


def test_contract_kind_relief_enum():
    assert ContractKind.RELIEF == "relief"
    assert "relief" in [k.value for k in ContractKind]

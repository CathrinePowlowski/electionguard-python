from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, Union

from .chaum_pedersen import ChaumPedersenProof
from .election_object_base import ElectionObjectBase
from .elgamal import ElGamalCiphertext, ElGamalPublicKey

from .group import ElementModP, ElementModQ

from .logs import log_warning

from .type import ContestId, GuardianId, SelectionId


@dataclass
class CiphertextCompensatedDecryptionSelection(ElectionObjectBase):
    """
    A compensated fragment of a Guardian's Partial Decryption of a selection generated by an available guardian
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    missing_guardian_id: GuardianId
    """
    The Missing Guardian for whom this share is calculated on behalf of
    """

    share: ElementModP
    """
    The Share of the decryption of a selection. `M_{i,l} in the spec`
    """

    recovery_key: ElementModP
    """
    The Recovery Public Key for the missing_guardian that corresponds to the available guardian's share of the secret
    """

    proof: ChaumPedersenProof
    """
    The Proof that the share was decrypted correctly
    """


ProofOrRecovery = Union[
    ChaumPedersenProof, Dict[GuardianId, CiphertextCompensatedDecryptionSelection]
]


@dataclass
class CiphertextDecryptionSelection(ElectionObjectBase):
    """
    A Guardian's Partial Decryption of a selection.  A CiphertextDecryptionSelection
    can be generated by a guardian directly, or it can be compensated for by a quoprum of guardians

    When the guardian generates this share directly, the `proof` field is populated with
    a `chaumPedersen` proof that the decryption share was generated correctly.

    When the share is generated on behalf of this guardian by other guardians, the `recovered_parts`
    collection is populated with the `CiphertextCompensatedDecryptionSelection` objects generated
    by each available guardian.
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    share: ElementModP
    """
    The Share of the decryption of a selection. `M_i` in the spec
    """

    proof: Optional[ChaumPedersenProof] = field(init=True, default=None)
    """
    The Proof that the share was decrypted correctly, if the guardian
    was available for decryption
    """

    recovered_parts: Optional[
        Dict[GuardianId, CiphertextCompensatedDecryptionSelection]
    ] = field(init=True, default=None)
    """
    the recovered parts of the decryption provided by available guardians,
    if the guardian was missing from decryption
    """

    def is_valid(
        self,
        message: ElGamalCiphertext,
        election_public_key: ElGamalPublicKey,
        extended_base_hash: ElementModQ,
    ) -> bool:
        """
        Verify that this CiphertextDecryptionSelection is valid for a
        specific ElGamal key pair, public key, and election context.

        :param message: the `ElGamalCiphertext` to compare
        :param election_public_key: the `ElementModP Election Public Key for the Guardian
        :param extended_base_hash: The `ElementModQ` election extended base hash.
        """
        # verify we have a proof or recovered parts
        if self.proof is None and self.recovered_parts is None:
            log_warning(
                (
                    f"CiphertextDecryptionSelection is_valid failed for guardian: {self.guardian_id} "
                    f"selection: {self.object_id} with missing data"
                )
            )
            return False

        if self.proof is not None and self.recovered_parts is not None:
            log_warning(
                (
                    f"CiphertextDecryptionSelection is_valid failed for guardian: {self.guardian_id} "
                    f"selection: {self.object_id} cannot have proof and recovery"
                )
            )
            return False

        if self.proof is not None and not self.proof.is_valid(
            message,
            election_public_key,
            self.share,
            extended_base_hash,
        ):
            log_warning(
                (
                    f"CiphertextDecryptionSelection is_valid failed for guardian: {self.guardian_id} "
                    f"selection: {self.object_id} with invalid proof"
                )
            )
            return False

        if self.recovered_parts is not None:
            for (
                _compensating_guardian_id,
                part,
            ) in self.recovered_parts.items():
                if not part.proof.is_valid(
                    message,
                    part.recovery_key,
                    part.share,
                    extended_base_hash,
                ):

                    log_warning(
                        (
                            f"CiphertextDecryptionSelection is_valid failed for guardian: {self.guardian_id} "
                            f"selection: {self.object_id} with invalid partial proof"
                        )
                    )
                    return False

        return True


def create_ciphertext_decryption_selection(
    object_id: str,
    guardian_id: GuardianId,
    share: ElementModP,
    proof_or_recovery: ProofOrRecovery,
) -> CiphertextDecryptionSelection:
    """
    Create a ciphertext decryption selection

    :param object_id: Object id
    :param guardian_id: Guardian id
    :param description_hash: Description hash
    :param share: Share
    :param proof_or_recovery: Proof or recovery
    """
    if isinstance(proof_or_recovery, ChaumPedersenProof):
        return CiphertextDecryptionSelection(
            object_id, guardian_id, share, proof=proof_or_recovery
        )
    if isinstance(proof_or_recovery, dict):
        return CiphertextDecryptionSelection(
            object_id,
            guardian_id,
            share,
            recovered_parts=proof_or_recovery,
        )
    log_warning(f"decryption share cannot assign {proof_or_recovery}")
    return CiphertextDecryptionSelection(
        object_id,
        guardian_id,
        share,
    )


@dataclass
class CiphertextDecryptionContest(ElectionObjectBase):
    """
    A Guardian's Partial Decryption of a contest
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    description_hash: ElementModQ
    """
    The ContestDescription Hash
    """

    selections: Dict[SelectionId, CiphertextDecryptionSelection]
    """
    the collection of decryption shares for this contest's selections
    """


@dataclass
class CiphertextCompensatedDecryptionContest(ElectionObjectBase):
    """
    A Guardian's Partial Decryption of a contest
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    missing_guardian_id: GuardianId
    """
    The Missing Guardian for whom this share is calculated on behalf of
    """

    description_hash: ElementModQ
    """
    The ContestDescription Hash
    """

    selections: Dict[SelectionId, CiphertextCompensatedDecryptionSelection]
    """
    the collection of decryption shares for this contest's selections
    """


@dataclass
class DecryptionShare(ElectionObjectBase):
    """
    A Guardian's Partial Decryption Share of a specific set of contests (Tally or Ballot)
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    public_key: ElGamalPublicKey
    """
    The election public key for the guardian
    """

    contests: Dict[ContestId, CiphertextDecryptionContest]
    """
    The collection of all contests in the ballot
    """


@dataclass
class CompensatedDecryptionShare(ElectionObjectBase):
    """
    A Compensated Partial Decryption Share generated by
    an available guardian on behalf of a missing guardian
    """

    guardian_id: GuardianId
    """
    The Available Guardian that this share belongs to
    """

    missing_guardian_id: GuardianId
    """
    The Missing Guardian for whom this share is calculated on behalf of
    """

    public_key: ElGamalPublicKey
    """
    The election public key for the guardian
    """

    contests: Dict[ContestId, CiphertextCompensatedDecryptionContest]
    """
    The collection of all contests in the ballot
    """


def get_shares_for_selection(
    selection_id: str,
    shares: Dict[GuardianId, DecryptionShare],
) -> Dict[GuardianId, Tuple[ElementModP, CiphertextDecryptionSelection]]:
    """
    Get all of the cast shares for a specific selection
    """
    selections: Dict[GuardianId, Tuple[ElementModP, CiphertextDecryptionSelection]] = {}
    for share in shares.values():
        for contest in share.contests.values():
            for selection in contest.selections.values():
                if selection.object_id == selection_id:
                    selections[share.guardian_id] = (share.public_key, selection)

    return selections

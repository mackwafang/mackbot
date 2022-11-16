from ..constants import AA_RATING_DESCRIPTOR

def get_aa_rating_descriptor(rating: int) -> str:
	return [AA_RATING_DESCRIPTOR[descriptor] for descriptor in AA_RATING_DESCRIPTOR if descriptor[0] <= rating < descriptor[1]][0]
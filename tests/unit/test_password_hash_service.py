from vstitchServices.passwordHashService import PasswordHashService


def test_hash_and_verify_roundtrip():
    service = PasswordHashService()
    hashed = service.hash_password("Str0ngPass!")
    assert hashed != "Str0ngPass!"
    assert service.verify_password("Str0ngPass!", hashed) is True


def test_verify_rejects_wrong_password():
    service = PasswordHashService()
    hashed = service.hash_password("Str0ngPass!")
    assert service.verify_password("WrongPass!", hashed) is False


def test_verify_handles_malformed_hash_gracefully():
    service = PasswordHashService()
    assert service.verify_password("anything", "not-a-real-bcrypt-hash") is False

// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CertificateAuth {
    struct Certificate {
        uint256 id;
        bytes32 hash;
        address issuer;
        uint256 timestamp;
    }

    mapping(bytes32 => Certificate) public certificates;
    uint256 public certificateCount = 0;

    event CertificateRegistered(uint256 id, bytes32 hash, address issuer, uint256 timestamp);

    // Register a new certificate (no duplicates allowed)
    function registerCertificate(bytes32 hash) public {
        require(certificates[hash].hash == 0x0, "Certificate already exists");

        certificateCount++;
        certificates[hash] = Certificate(certificateCount, hash, msg.sender, block.timestamp);

        emit CertificateRegistered(certificateCount, hash, msg.sender, block.timestamp);
    }

    // Verify if a certificate exists
    function verifyCertificate(bytes32 hash) public view returns (bool, uint256, address, uint256) {
        Certificate memory cert = certificates[hash];
        if (cert.hash == 0x0) {
            return (false, 0, address(0), 0);
        }
        return (true, cert.id, cert.issuer, cert.timestamp);
    }
}

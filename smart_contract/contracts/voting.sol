// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract Voting {
    struct Candidate {
        string name;
        uint voteCount;
    }

    struct Voter {
        bool isRegistered;
        bool hasVoted;
        uint votedForCandidateId; // Storing candidate ID/index
    }

    enum VotingPhase {
        Pending, // Voting has not started yet
        Active,  // Voting is ongoing
        Concluded // Voting has ended
    }

    address public admin;
    Candidate[] public candidates;
    mapping(address => Voter) public voters;

    uint public votingStartTime;
    uint public votingEndTime; // Renamed from votingDeadline for clarity
    VotingPhase public currentPhase;

    // Events
    event CandidateAdded(uint candidateId, string candidateName);
    event VoterRegistered(address voterAddress);
    event Voted(address voterAddress, uint candidateId);
    event VoteRevoked(address voterAddress, uint candidateId);
    event VotingPeriodSet(uint startTime, uint endTime);
    event VotingStarted(uint startTime);
    event VotingEnded(uint endTime);


    modifier onlyAdmin() {
        require(msg.sender == admin, "Not authorized: Only admin can perform this action.");
        _;
    }

    constructor() { // Duration can be set by admin later
        admin = msg.sender;
        currentPhase = VotingPhase.Pending; // Initially pending
    }

    // --- Candidate Management ---
    function addCandidate(string memory _name) public onlyAdmin {
        require(currentPhase == VotingPhase.Pending, "Cannot add candidates once voting has started or concluded.");
        candidates.push(Candidate({
            name: _name,
            voteCount: 0
        }));
        emit CandidateAdded(candidates.length - 1, _name);
    }

    function getCandidatesCount() public view returns (uint) {
        return candidates.length;
    }

    function getCandidate(uint _candidateId) public view returns (string memory name, uint voteCount) {
        require(_candidateId < candidates.length, "Invalid candidate ID.");
        return (candidates[_candidateId].name, candidates[_candidateId].voteCount);
    }
    
    // --- Voter Management ---
    function registerVoter(address _voterAddress) public onlyAdmin {
        require(!voters[_voterAddress].isRegistered, "Voter already registered.");
        // Optionally, restrict voter registration to certain phases, e.g., Pending or Active
        // require(currentPhase == VotingPhase.Pending || currentPhase == VotingPhase.Active, "Voter registration not allowed in current phase.");
        voters[_voterAddress] = Voter(true, false, 0); // Assuming 0 is not a valid candidateId or means "no vote"
        emit VoterRegistered(_voterAddress);
    }

    // --- Voting Process Management by Admin ---
    function setVotingPeriod(uint _startTime, uint _endTime) public onlyAdmin {
        require(currentPhase == VotingPhase.Pending, "Voting period can only be set when voting is pending.");
        require(_startTime < _endTime, "Start time must be before end time.");
        require(_startTime >= block.timestamp, "Start time cannot be in the past."); // Or allow past start time if admin is setting up an already started event

        votingStartTime = _startTime;
        votingEndTime = _endTime;
        emit VotingPeriodSet(_startTime, _endTime);
    }

    function startVoting() public onlyAdmin {
        require(currentPhase == VotingPhase.Pending, "Voting can only be started if it's pending.");
        require(votingEndTime > 0, "Voting end time must be set before starting.");

        // 确保当前区块时间在预设的结束时间之前
        require(block.timestamp < votingEndTime, "Cannot start voting if current time is already past the end time.");
        require(candidates.length > 1, "At least two candidates are required to start voting.");

        votingStartTime = block.timestamp; // 将投票开始时间设置为当前区块时间
        currentPhase = VotingPhase.Active;
        // 事件将发出实际的开始时间
        emit VotingStarted(votingStartTime); 
    }

    function endVoting() public onlyAdmin {
        require(currentPhase == VotingPhase.Active, "Voting can only be ended if it's active.");
        // Admin can end voting prematurely
        currentPhase = VotingPhase.Concluded;
        // Optionally update votingEndTime to block.timestamp if ending early
        // votingEndTime = block.timestamp; 
        emit VotingEnded(block.timestamp);
    }
    
    function extendVotingDeadline(uint _newEndTime) public onlyAdmin {
        require(currentPhase == VotingPhase.Active, "Can only extend deadline during active voting.");
        require(_newEndTime > votingEndTime, "New end time must be after current end time.");
        require(_newEndTime > block.timestamp, "New end time must be in the future.");
        votingEndTime = _newEndTime;
        emit VotingPeriodSet(votingStartTime, _newEndTime); // Re-emit with new end time
    }


    // --- Voting by Users ---
    modifier canVote() {
        require(currentPhase == VotingPhase.Active, "Voting is not active.");
        require(block.timestamp < votingEndTime, "Voting period has ended.");
        require(voters[msg.sender].isRegistered, "You are not a registered voter.");
        _;
    }

    function vote(uint _candidateId) public canVote {
        require(!voters[msg.sender].hasVoted, "Already voted.");
        require(_candidateId < candidates.length, "Invalid candidate ID.");

        voters[msg.sender].hasVoted = true;
        voters[msg.sender].votedForCandidateId = _candidateId;
        candidates[_candidateId].voteCount++;
        emit Voted(msg.sender, _candidateId);
    }

    function revokeVote() public canVote { // User can only revoke if they can vote (i.e., voting active)
        require(voters[msg.sender].hasVoted, "No vote to revoke.");

        uint candidateId = voters[msg.sender].votedForCandidateId;
        // No need to check if candidateId is valid here as it was valid when vote was cast.
        // However, ensure candidate still exists if candidates could be removed (not current design)
        candidates[candidateId].voteCount--;
        
        voters[msg.sender].hasVoted = false;
        // Resetting votedForCandidateId to a non-ID or specific "no vote" value might be cleaner.
        // For simplicity, we can leave it, as hasVoted is the primary check.
        // voters[msg.sender].votedForCandidateId = type(uint).max; // Example for "no vote"
        emit VoteRevoked(msg.sender, candidateId);
    }

    // --- View Functions ---
    function getVotingStatus() public view returns (VotingPhase phase, uint startTime, uint endTime, uint currentTime) {
        return (currentPhase, votingStartTime, votingEndTime, block.timestamp);
    }

    function getVoterInfo(address _voterAddress) public view returns (bool isRegistered, bool hasVoted, uint votedFor) {
        Voter storage voter = voters[_voterAddress];
        return (voter.isRegistered, voter.hasVoted, voter.votedForCandidateId);
    }
    
    // getCandidates remains similar, but you might want to return an array of structs
    // or separate arrays for names and counts as before.
    // For simplicity, I'm keeping a getter for individual candidate and count.
}
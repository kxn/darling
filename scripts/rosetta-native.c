// This runtime executes x86_64 instructions natively and does not use Rosetta.
_Bool rosetta_is_current_process_translated(void) { return 0; }
